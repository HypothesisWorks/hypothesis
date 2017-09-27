# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import time
import heapq
from enum import Enum
from random import Random, getrandbits
from weakref import WeakKeyDictionary
from collections import defaultdict

import attr

from hypothesis import settings as Settings
from hypothesis import Phase
from hypothesis.reporting import debug_report
from hypothesis.internal.compat import EMPTY_BYTES, Counter, ceil, \
    hbytes, hrange, int_to_text, int_to_bytes, bytes_from_list, \
    to_bytes_sequence, unicode_safe_repr
from hypothesis.utils.conventions import UniqueIdentifier
from hypothesis.internal.conjecture.data import MAX_DEPTH, Status, \
    StopTest, ConjectureData
from hypothesis.internal.conjecture.minimizer import minimize


class ExitReason(Enum):
    max_examples = 0
    max_iterations = 1
    timeout = 2
    max_shrinks = 3
    finished = 4
    flaky = 5


class RunIsComplete(Exception):
    pass


class ConjectureRunner(object):

    def __init__(
        self, test_function, settings=None, random=None,
        database_key=None,
    ):
        self._test_function = test_function
        self.settings = settings or Settings()
        self.last_data = None
        self.shrinks = 0
        self.call_count = 0
        self.event_call_counts = Counter()
        self.valid_examples = 0
        self.start_time = time.time()
        self.random = random or Random(getrandbits(128))
        self.database_key = database_key
        self.status_runtimes = {}
        self.events_to_strings = WeakKeyDictionary()

        self.target_selector = TargetSelector(self.random)

        # Tree nodes are stored in an array to prevent heavy nesting of data
        # structures. Branches are dicts mapping bytes to child nodes (which
        # will in general only be partially populated). Leaves are
        # ConjectureData objects that have been previously seen as the result
        # of following that path.
        self.tree = [{}]

        # A node is dead if there is nothing left to explore past that point.
        # Recursively, a node is dead if either it is a leaf or every byte
        # leads to a dead node when starting from here.
        self.dead = set()

        # We rewrite the byte stream at various points during parsing, to one
        # that will produce an equivalent result but is in some sense more
        # canonical. We keep track of these so that when walking the tree we
        # can identify nodes where the exact byte value doesn't matter and
        # treat all bytes there as equivalent. This significantly reduces the
        # size of the search space and removes a lot of redundant examples.

        # Maps tree indices where to the unique byte that is valid at that
        # point. Corresponds to data.write() calls.
        self.forced = {}

        # Maps tree indices to the maximum byte that is valid at that point.
        # Currently this is only used inside draw_bits, but it potentially
        # could get used elsewhere.
        self.capped = {}

        # Where a tree node consists of the beginning of a block we track the
        # size of said block. This allows us to tell when an example is too
        # short even if it goes off the unexplored region of the tree - if it
        # is at the beginning of a block of size 4 but only has 3 bytes left,
        # it's going to overrun the end of the buffer regardless of the
        # buffer contents.
        self.block_sizes = {}

        self.interesting_examples = {}
        self.covering_examples = {}

        self.shrunk_examples = set()

        self.tag_intern_table = {}

    def __tree_is_exhausted(self):
        return 0 in self.dead

    def test_function(self, data):
        self.call_count += 1
        try:
            self._test_function(data)
            data.freeze()
        except StopTest as e:
            if e.testcounter != data.testcounter:
                self.save_buffer(data.buffer)
                raise e
        except:
            self.save_buffer(data.buffer)
            raise
        finally:
            data.freeze()
            self.note_details(data)

        self.target_selector.add(data)

        self.debug_data(data)

        tags = frozenset(
            self.tag_intern_table.setdefault(t, t)
            for t in data.tags
        )
        data.tags = self.tag_intern_table.setdefault(tags, tags)

        if data.status == Status.VALID:
            self.valid_examples += 1
            for t in data.tags:
                existing = self.covering_examples.get(t)
                if (
                    existing is None or
                    sort_key(data.buffer) < sort_key(existing.buffer)
                ):
                    self.covering_examples[t] = data
                    if self.database is not None:
                        self.database.save(self.covering_key, data.buffer)
                        if existing is not None:
                            self.database.delete(
                                self.covering_key, existing.buffer)

        tree_node = self.tree[0]
        indices = []
        node_index = 0
        for i, b in enumerate(data.buffer):
            indices.append(node_index)
            if i in data.forced_indices:
                self.forced[node_index] = b
            try:
                self.capped[node_index] = data.capped_indices[i]
            except KeyError:
                pass
            try:
                node_index = tree_node[b]
            except KeyError:
                node_index = len(self.tree)
                self.tree.append({})
                tree_node[b] = node_index
            tree_node = self.tree[node_index]
            if node_index in self.dead:
                break

        for u, v in data.blocks:
            # This can happen if we hit a dead node when walking the buffer.
            # In that case we alrady have this section of the tree mapped.
            if u >= len(indices):
                break
            self.block_sizes[indices[u]] = v - u

        if data.status != Status.OVERRUN and node_index not in self.dead:
            self.dead.add(node_index)
            self.tree[node_index] = data

            for j in reversed(indices):
                if (
                    len(self.tree[j]) < self.capped.get(j, 255) + 1 and
                    j not in self.forced
                ):
                    break
                if set(self.tree[j].values()).issubset(self.dead):
                    self.dead.add(j)
                else:
                    break

        last_data_is_interesting = (
            self.last_data is not None and
            self.last_data.status == Status.INTERESTING
        )

        if data.status == Status.INTERESTING:
            first_call = len(self.interesting_examples) == 0

            key = data.interesting_origin
            changed = False
            try:
                existing = self.interesting_examples[key]
            except KeyError:
                changed = True
            else:
                if sort_key(data.buffer) < sort_key(existing.buffer):
                    self.downgrade_buffer(existing.buffer)
                    changed = True

            if changed:
                self.interesting_examples[key] = data
                self.shrunk_examples.discard(key)
                if last_data_is_interesting and not first_call:
                    self.shrinks += 1

            if not last_data_is_interesting or (
                sort_key(data.buffer) < sort_key(self.last_data.buffer) and
                data.interesting_origin ==
                self.last_data.interesting_origin
            ):
                self.last_data = data

            if self.shrinks >= self.settings.max_shrinks:
                self.exit_with(ExitReason.max_shrinks)
        elif (
            self.last_data is None or
            self.last_data.status < Status.INTERESTING
        ):
            self.last_data = data
        if (
            self.settings.timeout > 0 and
            time.time() >= self.start_time + self.settings.timeout
        ):
            self.exit_with(ExitReason.timeout)

        if not self.interesting_examples:
            if self.valid_examples >= self.settings.max_examples:
                self.exit_with(ExitReason.max_examples)
            if self.call_count >= max(
                self.settings.max_iterations, self.settings.max_examples
            ):
                self.exit_with(ExitReason.max_iterations)

        if self.__tree_is_exhausted():
            self.exit_with(ExitReason.finished)

    def save_buffer(self, buffer, key=None):
        if self.settings.database is not None:
            if key is None:
                key = self.database_key
            if key is None:
                return
            self.settings.database.save(key, hbytes(buffer))

    def downgrade_buffer(self, buffer):
        if self.settings.database is not None:
            self.settings.database.move(
                self.database_key, self.secondary_key, buffer)

    @property
    def secondary_key(self):
        return b'.'.join((self.database_key, b"secondary"))

    @property
    def covering_key(self):
        return b'.'.join((self.database_key, b"coverage"))

    def note_details(self, data):
        if data.status == Status.INTERESTING:
            if (
                self.last_data is None or
                self.last_data.status != Status.INTERESTING or
                self.last_data.interesting_origin == data.interesting_origin
            ):
                self.save_buffer(data.buffer)
            else:
                self.save_buffer(data.buffer, self.secondary_key)
        runtime = max(data.finish_time - data.start_time, 0.0)
        self.status_runtimes.setdefault(data.status, []).append(runtime)
        for event in set(map(self.event_to_string, data.events)):
            self.event_call_counts[event] += 1

    def debug(self, message):
        with self.settings:
            debug_report(message)

    def debug_data(self, data):
        buffer_parts = [u"["]
        for i, (u, v) in enumerate(data.blocks):
            if i > 0:
                buffer_parts.append(u" || ")
            buffer_parts.append(
                u', '.join(int_to_text(int(i)) for i in data.buffer[u:v]))
        buffer_parts.append(u']')

        status = unicode_safe_repr(data.status)

        if data.status == Status.INTERESTING:
            status = u'%s (%s)' % (
                status, unicode_safe_repr(data.interesting_origin,))

        self.debug(u'%d bytes %s -> %s, %s' % (
            data.index,
            u''.join(buffer_parts),
            status,
            data.output,
        ))

    def prescreen_buffer(self, buffer):
        """Attempt to rule out buffer as a possible interesting candidate.

        Returns False if we know for sure that running this buffer will not
        produce an interesting result. Returns True if it might (because it
        explores territory we have not previously tried).

        This is purely an optimisation to try to reduce the number of tests we
        run. "return True" would be a valid but inefficient implementation.

        """
        node_index = 0
        n = len(buffer)
        for k, b in enumerate(buffer):
            if node_index in self.dead:
                return False
            try:
                # The block size at that point provides a lower bound on how
                # many more bytes are required. If the buffer does not have
                # enough bytes to fulfill that block size then we can rule out
                # this buffer.
                if k + self.block_sizes[node_index] > n:
                    return False
            except KeyError:
                pass
            try:
                b = self.forced[node_index]
            except KeyError:
                pass
            try:
                b = min(b, self.capped[node_index])
            except KeyError:
                pass
            try:
                node_index = self.tree[node_index][b]
            except KeyError:
                return True
        else:
            return False

    def incorporate_new_buffer(self, buffer):
        assert self.last_data.status == Status.INTERESTING
        start = self.last_data.interesting_origin

        buffer = hbytes(buffer[:self.last_data.index])
        assert sort_key(buffer) < sort_key(self.last_data.buffer)

        if not self.prescreen_buffer(buffer):
            return False

        assert sort_key(buffer) <= sort_key(self.last_data.buffer)
        data = ConjectureData.for_buffer(buffer)
        self.test_function(data)
        assert self.last_data.interesting_origin == start
        return data is self.last_data

    def run(self):
        with self.settings:
            try:
                self._run()
            except RunIsComplete:
                pass
            if self.interesting_examples:
                self.last_data = max(
                    self.interesting_examples.values(),
                    key=lambda d: sort_key(d.buffer))
            if self.last_data is not None:
                self.debug_data(self.last_data)
            self.debug(
                u'Run complete after %d examples (%d valid) and %d shrinks' % (
                    self.call_count, self.valid_examples, self.shrinks,
                ))

    def _new_mutator(self):
        def draw_new(data, n):
            return uniform(self.random, n)

        def draw_existing(data, n):
            return self.last_data.buffer[data.index:data.index + n]

        def draw_smaller(data, n):
            existing = self.last_data.buffer[data.index:data.index + n]
            r = uniform(self.random, n)
            if r <= existing:
                return r
            return _draw_predecessor(self.random, existing)

        def draw_larger(data, n):
            existing = self.last_data.buffer[data.index:data.index + n]
            r = uniform(self.random, n)
            if r >= existing:
                return r
            return _draw_successor(self.random, existing)

        def reuse_existing(data, n):
            choices = data.block_starts.get(n, []) or \
                self.last_data.block_starts.get(n, [])
            if choices:
                i = self.random.choice(choices)
                return self.last_data.buffer[i:i + n]
            else:
                result = uniform(self.random, n)
                assert isinstance(result, hbytes)
                return result

        def flip_bit(data, n):
            buf = bytearray(
                self.last_data.buffer[data.index:data.index + n])
            i = self.random.randint(0, n - 1)
            k = self.random.randint(0, 7)
            buf[i] ^= (1 << k)
            return hbytes(buf)

        def draw_zero(data, n):
            return hbytes(b'\0' * n)

        def draw_max(data, n):
            return hbytes([255]) * n

        def draw_constant(data, n):
            return bytes_from_list([
                self.random.randint(0, 255)
            ] * n)

        def redraw_last(data, n):
            u = self.last_data.blocks[-1][0]
            if data.index + n <= u:
                return self.last_data.buffer[data.index:data.index + n]
            else:
                return uniform(self.random, n)

        options = [
            draw_new,
            redraw_last, redraw_last,
            reuse_existing, reuse_existing,
            draw_existing, draw_smaller, draw_larger,
            flip_bit,
            draw_zero, draw_max, draw_zero, draw_max,
            draw_constant,
        ]

        bits = [
            self.random.choice(options) for _ in hrange(3)
        ]

        def draw_mutated(data, n):
            if (
                data.index + n > len(self.last_data.buffer)
            ):
                result = uniform(self.random, n)
            else:
                result = self.random.choice(bits)(data, n)

            return self.__rewrite_for_novelty(
                data, self.__zero_bound(data, result))

        return draw_mutated

    def __rewrite(self, data, result):
        return self.__rewrite_for_novelty(
            data, self.__zero_bound(data, result)
        )

    def __zero_bound(self, data, result):
        """This tries to get the size of the generated data under control by
        replacing the result with zero if we are too deep or have already
        generated too much data.

        This causes us to enter "shrinking mode" there and thus reduce
        the size of the generated data.

        """
        if (
            data.depth * 2 >= MAX_DEPTH or
            (data.index + len(result)) * 2 >= self.settings.buffer_size
        ):
            if any(result):
                data.hit_zero_bound = True
            return hbytes(len(result))
        else:
            return result

    def __rewrite_for_novelty(self, data, result):
        """Take a block that is about to be added to data as the result of a
        draw_bytes call and rewrite it a small amount to ensure that the result
        will be novel: that is, not hit a part of the tree that we have fully
        explored.

        This is mostly useful for test functions which draw a small
        number of blocks.

        """
        assert isinstance(result, hbytes)
        try:
            node_index = data.__current_node_index
        except AttributeError:
            node_index = 0
            data.__current_node_index = node_index
            data.__hit_novelty = False
            data.__evaluated_to = 0

        if data.__hit_novelty:
            return result

        node = self.tree[node_index]

        for i in hrange(data.__evaluated_to, len(data.buffer)):
            node = self.tree[node_index]
            try:
                node_index = node[data.buffer[i]]
                assert node_index not in self.dead
                node = self.tree[node_index]
            except KeyError:
                data.__hit_novelty = True
                return result

        for i, b in enumerate(result):
            assert isinstance(b, int)
            try:
                new_node_index = node[b]
            except KeyError:
                data.__hit_novelty = True
                return result

            new_node = self.tree[new_node_index]

            if new_node_index in self.dead:
                if isinstance(result, hbytes):
                    result = bytearray(result)
                for c in range(256):
                    if c not in node:
                        assert c <= self.capped.get(node_index, c)
                        result[i] = c
                        data.__hit_novelty = True
                        return hbytes(result)
                    else:
                        new_node_index = node[c]
                        new_node = self.tree[new_node_index]
                        if new_node_index not in self.dead:
                            result[i] = c
                            break
                else:  # pragma: no cover
                    assert False, (
                        'Found a tree node which is live despite all its '
                        'children being dead.')
            node_index = new_node_index
            node = new_node
        assert node_index not in self.dead
        data.__current_node_index = node_index
        data.__evaluated_to = data.index + len(result)
        return hbytes(result)

    @property
    def database(self):
        if self.database_key is None:
            return None
        return self.settings.database

    def has_existing_examples(self):
        return (
            self.database is not None and
            Phase.reuse in self.settings.phases
        )

    def reuse_existing_examples(self):
        """If appropriate (we have a database and have been told to use it),
        try to reload existing examples from the database.

        If there are a lot we don't try all of them. We always try the
        smallest example in the database (which is guaranteed to be the
        last failure) and the largest (which is usually the seed example
        which the last failure came from but we don't enforce that). We
        then take a random sampling of the remainder and try those. Any
        examples that are no longer interesting are cleared out.

        """
        if self.has_existing_examples():
            self.debug('Reusing examples from database')
            # We have to do some careful juggling here. We have two database
            # corpora: The primary and secondary. The primary corpus is a
            # small set of minimized examples each of which has at one point
            # demonstrated a distinct bug. We want to retry all of these.

            # We also have a secondary corpus of examples that have at some
            # point demonstrated interestingness (currently only ones that
            # were previously non-minimal examples of a bug, but this will
            # likely expand in future). These are a good source of potentially
            # interesting examples, but there are a lot of them, so we down
            # sample the secondary corpus to a more manageable size.

            corpus = sorted(
                self.settings.database.fetch(self.database_key),
                key=sort_key
            )
            desired_size = max(2, ceil(0.1 * self.settings.max_examples))

            for extra_key in [self.secondary_key, self.covering_key]:
                if len(corpus) < desired_size:
                    extra_corpus = list(
                        self.settings.database.fetch(extra_key),
                    )

                    shortfall = desired_size - len(corpus)

                    if len(extra_corpus) <= shortfall:
                        extra = extra_corpus
                    else:
                        extra = self.random.sample(extra_corpus, shortfall)
                    extra.sort(key=sort_key)
                    corpus.extend(extra)

            for existing in corpus:
                self.last_data = ConjectureData.for_buffer(existing)
                try:
                    self.test_function(self.last_data)
                finally:
                    if self.last_data.status != Status.INTERESTING:
                        self.settings.database.delete(
                            self.database_key, existing)
                        self.settings.database.delete(
                            self.secondary_key, existing)

    def exit_with(self, reason):
        self.exit_reason = reason
        raise RunIsComplete()

    def generate_new_examples(self):
        if Phase.generate not in self.settings.phases:
            return

        zero_data = ConjectureData(
            max_length=self.settings.buffer_size,
            draw_bytes=lambda data, n: self.__rewrite_for_novelty(
                data, hbytes(n)))
        self.test_function(zero_data)

        count = 0
        while count < 10 and not self.interesting_examples:
            def draw_bytes(data, n):
                return self.__rewrite_for_novelty(
                    data, self.__zero_bound(data, uniform(self.random, n))
                )

            targets_found = len(self.covering_examples)

            self.last_data = ConjectureData(
                max_length=self.settings.buffer_size,
                draw_bytes=draw_bytes
            )
            self.test_function(self.last_data)
            self.last_data.freeze()

            if len(self.covering_examples) > targets_found:
                count = 0
            else:
                count += 1

        mutations = 0
        mutator = self._new_mutator()

        zero_bound_queue = []

        while not self.interesting_examples:
            if zero_bound_queue:
                # Whenever we generated an example and it hits a bound
                # which forces zero blocks into it, this creates a weird
                # distortion effect by making certain parts of the data
                # stream (especially ones to the right) much more likely
                # to be zero. We fix this by redistributing the generated
                # data by shuffling it randomly. This results in the
                # zero data being spread evenly throughout the buffer.
                # Hopefully the shrinking this causes will cause us to
                # naturally fail to hit the bound.
                # If it doesn't then we will queue the new version up again
                # (now with more zeros) and try again.
                overdrawn = zero_bound_queue.pop()
                buffer = bytearray(overdrawn.buffer)

                # These will have values written to them that are different
                # from what's in them anyway, so the value there doesn't
                # really "count" for distributional purposes, and if we
                # leave them in then they can cause the fraction of non
                # zero bytes to increase on redraw instead of decrease.
                for i in overdrawn.forced_indices:
                    buffer[i] = 0

                self.random.shuffle(buffer)
                buffer = hbytes(buffer)

                def draw_bytes(data, n):
                    result = buffer[data.index:data.index + n]
                    if len(result) < n:
                        result += hbytes(n - len(result))
                    return self.__rewrite(data, result)

                data = ConjectureData(
                    draw_bytes=draw_bytes,
                    max_length=self.settings.buffer_size,
                )
                self.test_function(data)
                data.freeze()
            else:
                target, last_data = self.target_selector.select()
                mutations += 1
                targets_found = len(self.covering_examples)
                prev_data = self.last_data
                data = ConjectureData(
                    draw_bytes=mutator,
                    max_length=self.settings.buffer_size
                )
                self.test_function(data)
                data.freeze()
                if (
                    data.status > prev_data.status or
                    len(self.covering_examples) > targets_found
                ):
                    mutations = 0
                elif (
                    data.status < prev_data.status or
                    not self.target_selector.has_tag(target, data) or
                    mutations >= self.settings.max_mutations
                ):
                    mutations = 0
                    mutator = self._new_mutator()
            if getattr(data, 'hit_zero_bound', False):
                zero_bound_queue.append(data)
            mutations += 1

    def _run(self):
        self.last_data = None
        self.start_time = time.time()

        self.reuse_existing_examples()
        self.generate_new_examples()

        if (
            Phase.shrink not in self.settings.phases or
            not self.interesting_examples
        ):
            self.exit_with(ExitReason.finished)

        for prev_data in sorted(
            self.interesting_examples.values(),
            key=lambda d: sort_key(d.buffer)
        ):
            assert prev_data.status == Status.INTERESTING
            data = ConjectureData.for_buffer(prev_data.buffer)
            self.test_function(data)
            if data.status != Status.INTERESTING:
                self.exit_with(ExitReason.flaky)

        while len(self.shrunk_examples) < len(self.interesting_examples):
            target, self.last_data = min([
                (k, v) for k, v in self.interesting_examples.items()
                if k not in self.shrunk_examples],
                key=lambda kv: (sort_key(kv[1].buffer), sort_key(repr(kv[0]))),
            )
            self.debug('Shrinking %r' % (target,))
            assert self.last_data.interesting_origin == target
            self.shrink()
            self.shrunk_examples.add(target)
        self.exit_with(ExitReason.finished)

    def try_buffer_with_rewriting_from(self, initial_attempt, v):
        initial_data = None
        node_index = 0
        for c in initial_attempt:
            try:
                node_index = self.tree[node_index][c]
            except KeyError:
                break
            node = self.tree[node_index]
            if isinstance(node, ConjectureData):
                initial_data = node
                break

        if initial_data is None:
            initial_data = ConjectureData.for_buffer(initial_attempt)
            self.test_function(initial_data)

        if initial_data.status == Status.INTERESTING:
            return initial_data is self.last_data

        # If this produced something completely invalid we ditch it
        # here rather than trying to persevere.
        if initial_data.status < Status.VALID:
            return False

        if len(initial_data.buffer) < v:
            return False

        lost_data = len(self.last_data.buffer) - \
            len(initial_data.buffer)

        # If this did not in fact cause the data size to shrink we
        # bail here because it's not worth trying to delete stuff from
        # the remainder.
        if lost_data <= 0:
            return False

        try_with_deleted = bytearray(initial_attempt)
        del try_with_deleted[v:v + lost_data]
        try_with_deleted.extend(hbytes(lost_data - 1))
        if self.incorporate_new_buffer(try_with_deleted):
            return True

        for r, s in self.last_data.intervals:
            if (
                r >= v and
                s - r <= lost_data and
                r < len(initial_data.buffer)
            ):
                try_with_deleted = bytearray(initial_attempt)
                del try_with_deleted[r:s]
                try_with_deleted.extend(hbytes(s - r - 1))
                if self.incorporate_new_buffer(try_with_deleted):
                    return True
        return False

    def delta_interval_deletion(self):
        """Attempt to delete every interval in the example."""

        self.debug('delta interval deletes')

        # We do a delta-debugging style thing here where we initially try to
        # delete many intervals at once and prune it down exponentially to
        # eventually only trying to delete one interval at a time.

        # I'm a little skeptical that this is helpful in general, but we've
        # got at least one benchmark where it does help.
        k = len(self.last_data.intervals) // 2
        while k > 0:
            i = 0
            while i + k <= len(self.last_data.intervals):
                bitmask = [True] * len(self.last_data.buffer)

                for u, v in self.last_data.intervals[i:i + k]:
                    for t in range(u, v):
                        bitmask[t] = False

                if not self.incorporate_new_buffer(hbytes(
                    b for b, v in zip(self.last_data.buffer, bitmask)
                    if v
                )):
                    i += k
            k //= 2

    def greedy_interval_deletion(self):
        """Attempt to delete every interval in the example."""

        self.debug('greedy interval deletes')
        i = 0
        while i < len(self.last_data.intervals):
            u, v = self.last_data.intervals[i]
            if not self.incorporate_new_buffer(
                self.last_data.buffer[:u] + self.last_data.buffer[v:]
            ):
                i += 1

    def coarse_block_replacement(self):
        """Attempts to zero every block. This is a very coarse pass that we
        only run once to attempt to remove some irrelevant detail. The main
        purpose of it is that if we manage to zero a lot of data then many
        attempted deletes become duplicates of each other, so we run fewer
        tests.

        If more blocks become possible to zero later that will be
        handled by minimize_individual_blocks. The point of this is
        simply to provide a fairly fast initial pass.

        """
        self.debug('Zeroing blocks')
        i = 0
        while i < len(self.last_data.blocks):
            buf = self.last_data.buffer
            u, v = self.last_data.blocks[i]
            assert u < v
            block = buf[u:v]
            if any(block):
                self.incorporate_new_buffer(
                    buf[:u] + hbytes(v - u) + buf[v:]
                )
            i += 1

    def minimize_duplicated_blocks(self):
        """Find blocks that have been duplicated in multiple places and attempt
        to minimize all of the duplicates simultaneously."""

        self.debug('Simultaneous shrinking of duplicated blocks')
        counts = Counter(
            self.last_data.buffer[u:v] for u, v in self.last_data.blocks
        )
        blocks = [
            k for k, count in
            counts.items()
            if count > 1
        ]

        thresholds = {}
        for u, v in self.last_data.blocks:
            b = self.last_data.buffer[u:v]
            thresholds[b] = v

        blocks.sort(reverse=True)
        blocks.sort(key=lambda b: counts[b] * len(b), reverse=True)
        for block in blocks:
            parts = [
                self.last_data.buffer[r:s]
                for r, s in self.last_data.blocks
            ]

            def replace(b):
                return hbytes(EMPTY_BYTES.join(
                    hbytes(b if c == block else c) for c in parts
                ))

            threshold = thresholds[block]

            minimize(
                block,
                lambda b: self.try_buffer_with_rewriting_from(
                    replace(b), threshold),
                random=self.random, full=False
            )

    def minimize_individual_blocks(self):
        self.debug('Shrinking of individual blocks')
        i = 0
        while i < len(self.last_data.blocks):
            u, v = self.last_data.blocks[i]
            minimize(
                self.last_data.buffer[u:v],
                lambda b: self.try_buffer_with_rewriting_from(
                    self.last_data.buffer[:u] + b +
                    self.last_data.buffer[v:], v
                ),
                random=self.random, full=False,
            )
            i += 1

    def reorder_blocks(self):
        self.debug('Reordering blocks')
        block_lengths = sorted(self.last_data.block_starts, reverse=True)
        for n in block_lengths:
            i = 1
            while i < len(self.last_data.block_starts.get(n, ())):
                j = i
                while j > 0:
                    buf = self.last_data.buffer
                    blocks = self.last_data.block_starts[n]
                    a_start = blocks[j - 1]
                    b_start = blocks[j]
                    a = buf[a_start:a_start + n]
                    b = buf[b_start:b_start + n]
                    if a <= b:
                        break
                    swapped = (
                        buf[:a_start] + b + buf[a_start + n:b_start] +
                        a + buf[b_start + n:])
                    assert len(swapped) == len(buf)
                    assert swapped < buf
                    if self.incorporate_new_buffer(swapped):
                        j -= 1
                    else:
                        break
                i += 1

    def shrink(self):
        # We assume that if an all-zero block of bytes is an interesting
        # example then we're not going to do better than that.
        # This might not technically be true: e.g. for integers() | booleans()
        # the simplest example is actually [1, 0]. Missing this case is fairly
        # harmless and this allows us to make various simplifying assumptions
        # about the structure of the data (principally that we're never
        # operating on a block of all zero bytes so can use non-zeroness as a
        # signpost of complexity).
        if (
            not any(self.last_data.buffer) or
            self.incorporate_new_buffer(hbytes(len(self.last_data.buffer)))
        ):
            return

        if self.has_existing_examples():
            # If we have any smaller examples in the secondary corpus, now is
            # a good time to try them to see if they work as shrinks. They
            # probably won't, but it's worth a shot and gives us a good
            # opportunity to clear out the database.

            # It's not worth trying the primary corpus because we already
            # tried all of those in the initial phase.
            corpus = sorted(
                self.settings.database.fetch(self.secondary_key),
                key=sort_key
            )
            for c in corpus:
                if sort_key(c) >= sort_key(self.last_data.buffer):
                    break
                elif self.incorporate_new_buffer(c):
                    break
                else:
                    self.settings.database.delete(self.secondary_key, c)

        # Coarse passes that are worth running once when the example is likely
        # to be "far from shrunk" but not worth repeating in a loop because
        # they are subsumed by more fine grained passes.
        self.delta_interval_deletion()
        self.coarse_block_replacement()

        change_counter = -1

        while self.shrinks > change_counter:
            change_counter = self.shrinks

            self.minimize_duplicated_blocks()
            self.minimize_individual_blocks()
            self.reorder_blocks()
            self.greedy_interval_deletion()

    def event_to_string(self, event):
        if isinstance(event, str):
            return event
        try:
            return self.events_to_strings[event]
        except KeyError:
            pass
        result = str(event)
        self.events_to_strings[event] = result
        return result


def _draw_predecessor(rnd, xs):
    r = bytearray()
    any_strict = False
    for x in to_bytes_sequence(xs):
        if not any_strict:
            c = rnd.randint(0, x)
            if c < x:
                any_strict = True
        else:
            c = rnd.randint(0, 255)
        r.append(c)
    return hbytes(r)


def _draw_successor(rnd, xs):
    r = bytearray()
    any_strict = False
    for x in to_bytes_sequence(xs):
        if not any_strict:
            c = rnd.randint(x, 255)
            if c > x:
                any_strict = True
        else:
            c = rnd.randint(0, 255)
        r.append(c)
    return hbytes(r)


def sort_key(buffer):
    return (len(buffer), buffer)


def uniform(random, n):
    return int_to_bytes(random.getrandbits(n * 8), n)


class SampleSet(object):
    """Set data type with the ability to sample uniformly at random from it.

    The mechanism is that we store the set in two parts: A mapping of
    values to their index in an array. Sampling uniformly at random then
    becomes simply a matter of sampling from the array, but we can use
    the index for efficient lookup to add and remove values.

    """
    __slots__ = ('__values', '__index')

    def __init__(self):
        self.__values = []
        self.__index = {}

    def __len__(self):
        return len(self.__values)

    def __repr__(self):
        return 'SampleSet(%r)' % (self.__values,)

    def add(self, value):
        assert value not in self.__index
        # Adding simply consists of adding the value to the end of the array
        # and updating the index.
        self.__index[value] = len(self.__values)
        self.__values.append(value)

    def remove(self, value):
        # To remove a value we first remove it from the index. But this leaves
        # us with the value still in the array, so we have to fix that. We
        # can't simply remove the value from the array, as that would a) Be an
        # O(n) operation and b) Leave the index completely wrong for every
        # value after that index.
        # So what we do is we take the last element of the array and place it
        # in the position of the value we just deleted (if the value was not
        # already the last element of the array. If it was then we don't have
        # to do anything extra). This reorders the array, but that's OK because
        # we don't care about its order, we just need to sample from it.
        i = self.__index.pop(value)
        last = self.__values.pop()
        if i < len(self.__values):
            self.__values[i] = last
            self.__index[last] = i

    def choice(self, random):
        return random.choice(self.__values)


@attr.s(slots=True, hash=True, cmp=True)
class Negated(object):
    tag = attr.ib()


universal = UniqueIdentifier('universal')


class TargetSelector(object):
    """Data structure for selecting targets to use for mutation.

    The goal is to do a good job of exploiting novelty in examples without
    getting too obsessed with any particular novel factor.

    Roughly speaking what we want to do is give each distinct coverage target
    equal amounts of time. However some coverage targets may be harder to fuzz
    than others, or may only appear in a very small minority of examples, so we
    don't want to let those dominate the testing.

    Targets are selected according to the following rules:

    1. We ideally want valid examples as our starting point. We ignore
       interesting examples entirely, and other than that we restrict ourselves
       to the best example status we've seen so far. If we've only seen
       OVERRUN examples we use those. If we've seen INVALID but not VALID
       examples we use those. Otherwise we use VALID examples.
    2. Among the examples we've seen with the right status, when asked to
       select a target, we select a coverage target and return that along with
       an example exhibiting that target uniformly at random.

    Coverage target selection proceeds as follows:

    1. Whenever we return an example from select, we update the usage count of
       each of its tags.
    2. Whenever we see an example, we add it to the list of examples for all of
       its tags.
    3. When selecting a tag, we select one with a minimal usage count. Among
       those of minimal usage count we select one with the fewest examples.
       Among those, we select one uniformly at random.

    This has the following desirable properties:

    1. When two coverage targets are intrinsically linked (e.g. when you have
       multiple lines in a conditional so that either all or none of them will
       be covered in a conditional) they are naturally deduplicated.
    2. Popular coverage targets will largely be ignored for considering what
       test to run - if every example exhibits a coverage target, picking an
       example because of that target is rather pointless.
    3. When we discover new coverage targets we immediately exploit them until
       we get to the point where we've spent about as much time on them as the
       existing targets.
    4. Among the interesting deduplicated coverage targets we essentially
       round-robin between them, but with a more consistent distribution than
       uniformly at random, which is important particularly for short runs.

    """

    def __init__(self, random):
        self.random = random
        self.best_status = Status.OVERRUN
        self.reset()

    def reset(self):
        self.examples_by_tags = defaultdict(list)
        self.tag_usage_counts = Counter()
        self.tags_by_score = defaultdict(SampleSet)
        self.scores_by_tag = {}
        self.scores = []
        self.mutation_counts = 0
        self.example_counts = 0
        self.non_universal_tags = set()
        self.universal_tags = None

    def add(self, data):
        if data.status == Status.INTERESTING:
            return
        if data.status < self.best_status:
            return
        if data.status > self.best_status:
            self.best_status = data.status
            self.reset()

        if self.universal_tags is None:
            self.universal_tags = set(data.tags)
        else:
            not_actually_universal = self.universal_tags - data.tags
            for t in not_actually_universal:
                self.universal_tags.remove(t)
                self.non_universal_tags.add(t)
                self.examples_by_tags[t] = list(
                    self.examples_by_tags[universal]
                )

        new_tags = data.tags - self.non_universal_tags

        for t in new_tags:
            self.non_universal_tags.add(t)
            self.examples_by_tags[Negated(t)] = list(
                self.examples_by_tags[universal]
            )

        self.example_counts += 1
        for t in self.tags_for(data):
            self.examples_by_tags[t].append(data)
            self.rescore(t)

    def has_tag(self, tag, data):
        if tag is universal:
            return True
        if isinstance(tag, Negated):
            return tag.tag not in data.tags
        return tag in data.tags

    def tags_for(self, data):
        yield universal
        for t in data.tags:
            yield t
        for t in self.non_universal_tags:
            if t not in data.tags:
                yield Negated(t)

    def rescore(self, tag):
        new_score = (
            self.tag_usage_counts[tag], len(self.examples_by_tags[tag]))
        try:
            old_score = self.scores_by_tag[tag]
        except KeyError:
            pass
        else:
            self.tags_by_score[old_score].remove(tag)
        self.scores_by_tag[tag] = new_score

        sample = self.tags_by_score[new_score]
        if len(sample) == 0:
            heapq.heappush(self.scores, new_score)
        sample.add(tag)

    def select_tag(self):
        while True:
            peek = self.scores[0]
            sample = self.tags_by_score[peek]
            if len(sample) == 0:
                heapq.heappop(self.scores)
            else:
                return sample.choice(self.random)

    def select_example_for_tag(self, t):
        return self.random.choice(self.examples_by_tags[t])

    def select(self):
        t = self.select_tag()
        self.mutation_counts += 1
        result = self.select_example_for_tag(t)
        assert self.has_tag(t, result)
        for s in self.tags_for(result):
            self.tag_usage_counts[s] += 1
            self.rescore(s)
        return t, result
