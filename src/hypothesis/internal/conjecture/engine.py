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
from enum import Enum
from random import Random, getrandbits
from weakref import WeakKeyDictionary

from hypothesis import settings as Settings
from hypothesis import Phase
from hypothesis.reporting import debug_report
from hypothesis.internal.compat import EMPTY_BYTES, Counter, ceil, \
    hbytes, hrange, text_type, int_to_text, bytes_from_list, \
    to_bytes_sequence, unicode_safe_repr
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

    def __tree_is_exhausted(self):
        return 0 in self.dead

    def new_buffer(self):
        assert not self.__tree_is_exhausted()

        def draw_bytes(data, n, distribution):
            return self.__rewrite_for_novelty(
                data, self.__zero_bound(data, distribution(self.random, n))
            )

        self.last_data = ConjectureData(
            max_length=self.settings.buffer_size,
            draw_bytes=draw_bytes
        )
        self.test_function(self.last_data)
        self.last_data.freeze()

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

        self.debug_data(data)
        if data.status >= Status.VALID:
            self.valid_examples += 1

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

        if (
            data.status == Status.INTERESTING and (
                not last_data_is_interesting or
                sort_key(data.buffer) < sort_key(self.last_data.buffer)
            )
        ):
            self.last_data = data
            if last_data_is_interesting:
                self.shrinks += 1
                if self.shrinks >= self.settings.max_shrinks:
                    self.exit_reason = ExitReason.max_shrinks
                    raise RunIsComplete()

    def consider_new_test_data(self, data):
        # Transition rules:
        #   1. Transition cannot decrease the status
        #   2. Any transition which increases the status is valid
        #   3. If the previous status was interesting, only shrinking
        #      transitions are allowed.
        if data.buffer == self.last_data.buffer:
            return False
        if self.last_data.status < data.status:
            return True
        if self.last_data.status > data.status:
            return False
        if data.status == Status.INVALID:
            return data.index >= self.last_data.index
        if data.status == Status.OVERRUN:
            return data.overdraw <= self.last_data.overdraw
        assert data.status == Status.VALID
        return True

    def save_buffer(self, buffer):
        if (
            self.settings.database is not None and
            self.database_key is not None
        ):
            self.settings.database.save(self.database_key, hbytes(buffer))

    def note_details(self, data):
        if data.status == Status.INTERESTING:
            self.save_buffer(data.buffer)
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

        self.debug(u'%d bytes %s -> %s, %s' % (
            data.index,
            u''.join(buffer_parts),
            unicode_safe_repr(data.status),
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
        if (
            self.settings.timeout > 0 and
            time.time() >= self.start_time + self.settings.timeout
        ):
            self.exit_reason = ExitReason.timeout
            raise RunIsComplete()

        buffer = hbytes(buffer[:self.last_data.index])
        assert sort_key(buffer) < sort_key(self.last_data.buffer)

        if not self.prescreen_buffer(buffer):
            return False

        assert sort_key(buffer) <= sort_key(self.last_data.buffer)
        data = ConjectureData.for_buffer(buffer)
        self.test_function(data)
        return data is self.last_data

    def run(self):
        with self.settings:
            try:
                self._run()
            except RunIsComplete:
                pass
            self.debug(
                u'Run complete after %d examples (%d valid) and %d shrinks' % (
                    self.call_count, self.valid_examples, self.shrinks,
                ))

    def _new_mutator(self):
        def draw_new(data, n, distribution):
            return distribution(self.random, n)

        def draw_existing(data, n, distribution):
            return self.last_data.buffer[data.index:data.index + n]

        def draw_smaller(data, n, distribution):
            existing = self.last_data.buffer[data.index:data.index + n]
            r = distribution(self.random, n)
            if r <= existing:
                return r
            return _draw_predecessor(self.random, existing)

        def draw_larger(data, n, distribution):
            existing = self.last_data.buffer[data.index:data.index + n]
            r = distribution(self.random, n)
            if r >= existing:
                return r
            return _draw_successor(self.random, existing)

        def reuse_existing(data, n, distribution):
            choices = data.block_starts.get(n, []) or \
                self.last_data.block_starts.get(n, [])
            if choices:
                i = self.random.choice(choices)
                return self.last_data.buffer[i:i + n]
            else:
                result = distribution(self.random, n)
                assert isinstance(result, hbytes)
                return result

        def flip_bit(data, n, distribution):
            buf = bytearray(
                self.last_data.buffer[data.index:data.index + n])
            i = self.random.randint(0, n - 1)
            k = self.random.randint(0, 7)
            buf[i] ^= (1 << k)
            return hbytes(buf)

        def draw_zero(data, n, distribution):
            return hbytes(b'\0' * n)

        def draw_max(data, n, distribution):
            return hbytes([255]) * n

        def draw_constant(data, n, distribution):
            return bytes_from_list([
                self.random.randint(0, 255)
            ] * n)

        options = [
            draw_new,
            reuse_existing, reuse_existing,
            draw_existing, draw_smaller, draw_larger,
            flip_bit,
            draw_zero, draw_max, draw_zero, draw_max,
            draw_constant,
        ]

        bits = [
            self.random.choice(options) for _ in hrange(3)
        ]

        def draw_mutated(data, n, distribution):
            if (
                data.index + n > len(self.last_data.buffer)
            ):
                result = distribution(self.random, n)
            else:
                result = self.random.choice(bits)(data, n, distribution)

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

    def has_existing_examples(self):
        return (
            self.settings.database is not None and
            self.database_key is not None and
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
            corpus = sorted(
                self.settings.database.fetch(self.database_key),
                key=sort_key
            )

            desired_size = max(2, ceil(0.1 * self.settings.max_examples))

            if desired_size < len(corpus):
                new_corpus = [corpus[0], corpus[-1]]
                n_boost = max(desired_size - 2, 0)
                new_corpus.extend(self.random.sample(corpus[1:-1], n_boost))
                corpus = new_corpus
                corpus.sort(key=sort_key)

            for existing in corpus:
                if self.valid_examples >= self.settings.max_examples:
                    self.exit_with(ExitReason.max_examples)
                if self.call_count >= max(
                    self.settings.max_iterations, self.settings.max_examples
                ):
                    self.exit_with(ExitReason.max_iterations)
                data = ConjectureData.for_buffer(existing)
                self.test_function(data)
                data.freeze()
                self.last_data = data
                self.consider_new_test_data(data)
                if data.status == Status.INTERESTING:
                    assert data.status == Status.INTERESTING
                    self.last_data = data
                    break
                else:
                    self.settings.database.delete(
                        self.database_key, existing)

    def exit_with(self, reason):
        self.exit_reason = reason
        raise RunIsComplete()

    def _run(self):
        self.last_data = None
        mutations = 0
        start_time = time.time()

        self.reuse_existing_examples()

        if (
            Phase.generate in self.settings.phases and not
            self.__tree_is_exhausted()
        ):
            if (
                self.last_data is None or
                self.last_data.status < Status.INTERESTING
            ):
                self.new_buffer()

            mutator = self._new_mutator()

            zero_bound_queue = []

            while (
                self.last_data.status != Status.INTERESTING and
                not self.__tree_is_exhausted()
            ):
                if self.valid_examples >= self.settings.max_examples:
                    self.exit_reason = ExitReason.max_examples
                    return
                if self.call_count >= max(
                    self.settings.max_iterations, self.settings.max_examples
                ):
                    self.exit_reason = ExitReason.max_iterations
                    return
                if (
                    self.settings.timeout > 0 and
                    time.time() >= start_time + self.settings.timeout
                ):
                    self.exit_reason = ExitReason.timeout
                    return
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

                    if buffer == overdrawn.buffer:
                        continue

                    def draw_bytes(data, n, distribution):
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
                elif mutations >= self.settings.max_mutations:
                    mutations = 0
                    data = self.new_buffer()
                    mutator = self._new_mutator()
                else:
                    data = ConjectureData(
                        draw_bytes=mutator,
                        max_length=self.settings.buffer_size
                    )
                    self.test_function(data)
                    data.freeze()
                    prev_data = self.last_data
                    if self.consider_new_test_data(data):
                        self.last_data = data
                        if data.status > prev_data.status:
                            mutations = 0
                    else:
                        mutator = self._new_mutator()
                if getattr(data, 'hit_zero_bound', False):
                    zero_bound_queue.append(data)
                mutations += 1

        if self.__tree_is_exhausted():
            self.exit_reason = ExitReason.finished
            return

        data = self.last_data
        if data is None:
            self.exit_reason = ExitReason.finished
            return
        assert isinstance(data.output, text_type)

        if self.settings.max_shrinks <= 0:
            self.exit_reason = ExitReason.max_shrinks
            return

        if Phase.shrink not in self.settings.phases:
            self.exit_reason = ExitReason.finished
            return

        data = ConjectureData.for_buffer(self.last_data.buffer)
        self.test_function(data)
        if data.status != Status.INTERESTING:
            self.exit_reason = ExitReason.flaky
            return

        self.shrink()

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
            self.last_data = initial_data
            return True

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
        attempted deletes become duplicates of eachother, so we run fewer
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
            self.exit_reason = ExitReason.finished
            return

        if self.has_existing_examples():
            corpus = sorted(
                self.settings.database.fetch(self.database_key),
                key=sort_key
            )
            # We always have self.last_data.buffer in the database because
            # we save every interesting example. This means we will always
            # trigger the first break and thus never exit the loop normally.
            for c in corpus:  # pragma: no branch
                if sort_key(c) >= sort_key(self.last_data.buffer):
                    break
                elif self.incorporate_new_buffer(c):
                    break
                else:
                    self.settings.database.delete(self.database_key, c)

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

        self.exit_reason = ExitReason.finished

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
