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
    hbytes, hrange, text_type, int_to_text, int_to_bytes, \
    bytes_from_list, to_bytes_sequence, unicode_safe_repr
from hypothesis.internal.conjecture.data import MAX_DEPTH, Status, \
    StopTest, ConjectureData
from hypothesis.internal.conjecture.minimizer import minimize
from hypothesis.internal.conjecture.tree import LanguageCache


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

        self.interesting_examples = {}
        self.shrunk_examples = set()

        self.language = LanguageCache()

    def new_buffer(self):
        assert not self.language.tree_is_exhausted()

        def draw_bytes(data, n):
            return self.language.rewrite_for_novelty(
                data, self.__zero_bound(data, uniform(self.random, n))
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

        self.language.add(data)

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
        return self.language.prescreen_buffer(buffer)

    def incorporate_new_buffer(self, buffer):
        assert self.last_data.status == Status.INTERESTING
        start = self.last_data.interesting_origin
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

        def draw_mutated(data, n):
            if (
                data.index + n > len(self.last_data.buffer)
            ):
                result = uniform(self.random, n)
            else:
                result = self.random.choice(bits)(data, n)

            return self.language.rewrite_for_novelty(
                data, self.__zero_bound(data, result))

        return draw_mutated

    def __rewrite(self, data, result):
        return self.language.rewrite_for_novelty(
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

            if len(corpus) < desired_size:
                secondary_corpus = list(
                    self.settings.database.fetch(self.secondary_key),
                )

                shortfall = desired_size - len(corpus)

                if len(secondary_corpus) <= shortfall:
                    extra = secondary_corpus
                else:
                    extra = self.random.sample(secondary_corpus, shortfall)
                extra.sort(key=sort_key)
                corpus.extend(extra)

            for existing in corpus:
                if self.valid_examples >= self.settings.max_examples:
                    self.exit_with(ExitReason.max_examples)
                if self.call_count >= max(
                    self.settings.max_iterations, self.settings.max_examples
                ):
                    self.exit_with(ExitReason.max_iterations)
                self.last_data = ConjectureData.for_buffer(existing)
                self.test_function(self.last_data)
                if self.last_data.status != Status.INTERESTING:
                    self.settings.database.delete(
                        self.database_key, existing)
                    self.settings.database.delete(
                        self.secondary_key, existing)

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
            self.language.tree_is_exhausted()
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
                not self.language.tree_is_exhausted()
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

        if self.language.tree_is_exhausted():
            self.exit_reason = ExitReason.finished
            return

        data = self.last_data
        if data is None:
            self.exit_reason = ExitReason.finished
            return
        assert isinstance(data.output, text_type)

        if Phase.shrink not in self.settings.phases:
            self.exit_reason = ExitReason.finished
            return

        data = ConjectureData.for_buffer(self.last_data.buffer)
        self.test_function(data)
        if data.status != Status.INTERESTING:
            self.exit_reason = ExitReason.flaky
            return

        while len(self.shrunk_examples) < len(self.interesting_examples):
            target, d = min([
                (k, v) for k, v in self.interesting_examples.items()
                if k not in self.shrunk_examples],
                key=lambda kv: (sort_key(kv[1].buffer), sort_key(repr(kv[0]))),
            )
            self.debug('Shrinking %r' % (target,))
            self.last_data = d
            assert self.last_data.interesting_origin == target
            self.shrink()
            self.shrunk_examples.add(target)

    def try_buffer_with_rewriting_from(self, initial_attempt, v):
        result = self.language.cached_answer(initial_attempt)
        if result is None:
            initial_data = ConjectureData.for_buffer(initial_attempt)
            self.test_function(initial_data)
            status = initial_data.status
            length = len(initial_data.buffer)
            origin = initial_data.interesting_origin
        else:
            status, length, origin = result

        if status == Status.INTERESTING:
            return origin == self.last_data.interesting_origin

        # If this produced something completely invalid we ditch it
        # here rather than trying to persevere.
        if status < Status.VALID:
            return False

        if length < v:
            return False

        lost_data = len(self.last_data.buffer) - length

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
                r < length
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
            self.exit_reason = ExitReason.finished
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


def uniform(random, n):
    return int_to_bytes(random.getrandbits(n * 8), n)
