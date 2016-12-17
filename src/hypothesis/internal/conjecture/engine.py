# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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
from hypothesis.internal.compat import hbytes, hrange, Counter, \
    text_type, bytes_from_list, to_bytes_sequence, unicode_safe_repr
from hypothesis.internal.conjecture.data import Status, StopTest, TestData
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


class TestRunner(object):

    def __init__(
        self, test_function, settings=None, random=None,
        database_key=None,
    ):
        self._test_function = test_function
        self.settings = settings or Settings()
        self.last_data = None
        self.changed = 0
        self.shrinks = 0
        self.call_count = 0
        self.event_call_counts = Counter()
        self.valid_examples = 0
        self.start_time = time.time()
        self.random = random or Random(getrandbits(128))
        self.database_key = database_key
        self.seen = set()
        self.duplicates = 0
        self.status_runtimes = {}
        self.events_to_strings = WeakKeyDictionary()

    def new_buffer(self):
        self.last_data = TestData(
            max_length=self.settings.buffer_size,
            draw_bytes=lambda data, n, distribution:
            distribution(self.random, n)
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
        if (
            data.status == Status.INTERESTING and (
                self.last_data is None or
                data.buffer != self.last_data.buffer
            )
        ):
            self.debug_data(data)
        if data.status >= Status.VALID:
            self.valid_examples += 1

    def consider_new_test_data(self, data):
        # Transition rules:
        #   1. Transition cannot decrease the status
        #   2. Any transition which increases the status is valid
        #   3. If the previous status was interesting, only shrinking
        #      transitions are allowed.
        key = hbytes(data.buffer)
        if key in self.seen:
            self.duplicates += 1
            return False
        self.seen.add(key)
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
        if data.status == Status.INTERESTING:
            assert len(data.buffer) <= len(self.last_data.buffer)
            if len(data.buffer) == len(self.last_data.buffer):
                assert data.buffer < self.last_data.buffer
            return True
        return True

    def save_buffer(self, buffer):
        if (
            self.settings.database is not None and
            self.database_key is not None and
            Phase.reuse in self.settings.phases
        ):
            self.settings.database.save(
                self.database_key, hbytes(buffer)
            )

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
        self.debug(u'%d bytes %s -> %s, %s' % (
            data.index,
            unicode_safe_repr(list(data.buffer[:data.index])),
            unicode_safe_repr(data.status),
            data.output,
        ))

    def incorporate_new_buffer(self, buffer):
        if buffer in self.seen:
            return False
        assert self.last_data.status == Status.INTERESTING
        if (
            self.settings.timeout > 0 and
            time.time() >= self.start_time + self.settings.timeout
        ):
            self.exit_reason = ExitReason.timeout
            raise RunIsComplete()
        buffer = buffer[:self.last_data.index]
        if sort_key(buffer) >= sort_key(self.last_data.buffer):
            return False
        assert sort_key(buffer) <= sort_key(self.last_data.buffer)
        data = TestData.for_buffer(buffer)
        self.test_function(data)
        if self.consider_new_test_data(data):
            self.shrinks += 1
            self.last_data = data
            if self.shrinks >= self.settings.max_shrinks:
                self.exit_reason = ExitReason.max_shrinks
                raise RunIsComplete()
            self.last_data = data
            self.changed += 1
            return True
        return False

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
                return distribution(self.random, n)

        def flip_bit(data, n, distribution):
            buf = bytearray(
                self.last_data.buffer[data.index:data.index + n])
            i = self.random.randint(0, n - 1)
            k = self.random.randint(0, 7)
            buf[i] ^= (1 << k)
            return hbytes(buf)

        def draw_zero(data, n, distribution):
            return b'\0' * n

        def draw_constant(data, n, distribution):
            return bytes_from_list([
                self.random.randint(0, 255)
            ] * n)

        options = [
            draw_new,
            reuse_existing, reuse_existing,
            draw_existing, draw_smaller, draw_larger,
            flip_bit, draw_zero, draw_constant,
        ]

        bits = [
            self.random.choice(options) for _ in hrange(3)
        ]

        def draw_mutated(data, n, distribution):
            if (
                data.index + n > len(self.last_data.buffer)
            ):
                return distribution(self.random, n)
            return self.random.choice(bits)(data, n, distribution)
        return draw_mutated

    def _run(self):
        self.last_data = None
        mutations = 0
        start_time = time.time()

        if (
            self.settings.database is not None and
            self.database_key is not None
        ):
            corpus = sorted(
                self.settings.database.fetch(self.database_key),
                key=lambda d: (len(d), d)
            )
            for existing in corpus:
                if self.valid_examples >= self.settings.max_examples:
                    self.exit_reason = ExitReason.max_examples
                    return
                if self.call_count >= max(
                    self.settings.max_iterations, self.settings.max_examples
                ):
                    self.exit_reason = ExitReason.max_iterations
                    return
                data = TestData.for_buffer(existing)
                self.test_function(data)
                data.freeze()
                self.last_data = data
                if data.status < Status.VALID:
                    self.settings.database.delete(
                        self.database_key, existing)
                elif data.status == Status.VALID:
                    # Incremental garbage collection! we store a lot of
                    # examples in the DB as we shrink: Those that stay
                    # interesting get kept, those that become invalid get
                    # dropped, but those that are merely valid gradually go
                    # away over time.
                    if self.random.randint(0, 2) == 0:
                        self.settings.database.delete(
                            self.database_key, existing)
                else:
                    assert data.status == Status.INTERESTING
                    self.last_data = data
                    break

        if Phase.generate in self.settings.phases:
            if (
                self.last_data is None or
                self.last_data.status < Status.INTERESTING
            ):
                self.new_buffer()

            mutator = self._new_mutator()
            while self.last_data.status != Status.INTERESTING:
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
                if mutations >= self.settings.max_mutations:
                    mutations = 0
                    self.new_buffer()
                    mutator = self._new_mutator()
                else:
                    data = TestData(
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

                mutations += 1

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

        if not self.last_data.buffer:
            self.exit_reason = ExitReason.finished
            return

        data = TestData.for_buffer(self.last_data.buffer)
        self.test_function(data)
        if data.status != Status.INTERESTING:
            self.exit_reason = ExitReason.flaky
            return

        change_counter = -1

        while self.changed > change_counter:
            change_counter = self.changed

            self.debug('Random interval deletes')
            failed_deletes = 0
            while self.last_data.intervals and failed_deletes < 10:
                if self.random.randint(0, 1):
                    u, v = self.random.choice(self.last_data.intervals)
                else:
                    n = len(self.last_data.buffer) - 1
                    u, v = sorted((
                        self.random.choice(self.last_data.intervals)
                    ))
                if (
                    v < len(self.last_data.buffer)
                ) and self.incorporate_new_buffer(
                    self.last_data.buffer[:u] +
                    self.last_data.buffer[v:]
                ):
                    failed_deletes = 0
                else:
                    failed_deletes += 1

            self.debug('Structured interval deletes')
            i = 0
            while i < len(self.last_data.intervals):
                u, v = self.last_data.intervals[i]
                if not self.incorporate_new_buffer(
                    self.last_data.buffer[:u] +
                    self.last_data.buffer[v:]
                ):
                    i += 1

            if change_counter != self.changed:
                self.debug('Restarting')
                continue

            self.debug('Lexicographical minimization of whole buffer')
            minimize(
                self.last_data.buffer, self.incorporate_new_buffer,
                cautious=True
            )

            if change_counter != self.changed:
                self.debug('Restarting')
                continue

            self.debug('Replacing blocks with simpler blocks')
            i = 0
            while i < len(self.last_data.blocks):
                u, v = self.last_data.blocks[i]
                buf = self.last_data.buffer
                block = buf[u:v]
                n = v - u
                all_blocks = sorted(set([bytes(n)] + [
                    buf[a:a + n]
                    for a in self.last_data.block_starts[n]
                ]))
                better_blocks = all_blocks[:all_blocks.index(block)]
                for b in better_blocks:
                    if self.incorporate_new_buffer(
                        buf[:u] + b + buf[v:]
                    ):
                        break
                i += 1

            self.debug('Simultaneous shrinking of duplicated blocks')
            block_counter = -1
            while block_counter < self.changed:
                block_counter = self.changed
                blocks = [
                    k for k, count in
                    Counter(
                        self.last_data.buffer[u:v]
                        for u, v in self.last_data.blocks).items()
                    if count > 1
                ]
                for block in blocks:
                    parts = [
                        self.last_data.buffer[r:s]
                        for r, s in self.last_data.blocks
                    ]

                    def replace(b):
                        return b''.join(
                            bytes(b if c == block else c) for c in parts
                        )
                    minimize(
                        block,
                        lambda b: self.incorporate_new_buffer(replace(b)),
                        self.random
                    )

            self.debug('Shrinking of individual blocks')
            i = 0
            while i < len(self.last_data.blocks):
                u, v = self.last_data.blocks[i]
                minimize(
                    self.last_data.buffer[u:v],
                    lambda b: self.incorporate_new_buffer(
                        self.last_data.buffer[:u] + b +
                        self.last_data.buffer[v:],
                    ), self.random
                )
                i += 1

            self.debug('Replacing intervals with simpler intervals')

            interval_counter = -1
            while interval_counter != self.changed:
                interval_counter = self.changed
                i = 0
                alternatives = None
                while i < len(self.last_data.intervals):
                    if alternatives is None:
                        alternatives = sorted(set(
                            self.last_data.buffer[u:v]
                            for u, v in self.last_data.intervals), key=len)
                    u, v = self.last_data.intervals[i]
                    for a in alternatives:
                        buf = self.last_data.buffer
                        if (
                            len(a) < v - u or
                            (len(a) == (v - u) and a < buf[u:v])
                        ):
                            if self.incorporate_new_buffer(
                                buf[:u] + a + buf[v:]
                            ):
                                alternatives = None
                                break
                    i += 1

            if change_counter != self.changed:
                self.debug('Restarting')
                continue

            self.debug('Shuffling suffixes while shrinking %r' % (
                self.last_data.bind_points,
            ))
            b = 0
            while b < len(self.last_data.bind_points):
                cutoff = sorted(self.last_data.bind_points)[b]

                def test_value(prefix):
                    for t in hrange(5):
                        alphabet = {}
                        for i, j in self.last_data.blocks[b:]:
                            alphabet.setdefault(j - i, []).append((i, j))
                        if t > 0:
                            for v in alphabet.values():
                                self.random.shuffle(v)
                        buf = bytearray(prefix)
                        for i, j in self.last_data.blocks[b:]:
                            u, v = alphabet[j - i].pop()
                            buf.extend(self.last_data.buffer[u:v])
                        if self.incorporate_new_buffer(hbytes(buf)):
                            return True
                    return False
                minimize(
                    self.last_data.buffer[:cutoff], test_value, cautious=True
                )
                b += 1

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
