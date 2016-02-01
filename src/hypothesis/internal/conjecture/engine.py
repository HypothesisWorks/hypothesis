# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import time
from random import Random

from hypothesis import settings as Settings
from hypothesis.reporting import debug_report
from hypothesis.internal.compat import Counter
from hypothesis.internal.conjecture.data import Status, StopTest, TestData


class RunIsComplete(Exception):
    pass


class TestRunner(object):

    def __init__(
        self, test_function, settings, random=None
    ):
        self._test_function = test_function
        self.settings = settings or Settings()
        self.last_data = None
        self.changed = 0
        self.shrinks = 0
        self.examples_considered = 0
        self.iterations = 0
        self.valid_examples = 0
        self.start_time = time.time()
        self.random = random or Random()

    def new_buffer(self):
        self.last_data = TestData(
            max_length=self.settings.buffer_size,
            draw_bytes=lambda data, n, distribution:
            distribution(self.random, n)
        )
        self.test_function(self.last_data)
        self.last_data.freeze()

    def test_function(self, data):
        self.iterations += 1
        try:
            self._test_function(data)
        except StopTest as e:
            if e.uuid != data.uuid:
                raise e
        if data.status >= Status.VALID:
            self.valid_examples += 1

    def consider_new_test_data(self, data):
        # Transition rules:
        #   1. Transition cannot decrease the status
        #   2. Any transition which increases the status is valid
        #   3. If the previous status was interesting, only shrinking
        #      transitions are allowed.
        if self.last_data.status < data.status:
            return True
        if self.last_data.status > data.status:
            return False
        if data.status == Status.INVALID:
            return data.index >= self.last_data.index
        if data.status == Status.OVERRUN:
            return data.index <= self.last_data.index
        if data.status == Status.INTERESTING:
            assert len(data.buffer) <= len(self.last_data.buffer)
            if len(data.buffer) == len(self.last_data.buffer):
                assert data.buffer < self.last_data.buffer
            return True
        return True

    def incorporate_new_buffer(self, buffer):
        if (
            self.settings.timeout > 0 and
            time.time() >= self.start_time + self.settings.timeout
        ):
            raise RunIsComplete()
        self.examples_considered += 1
        if (
            len(buffer) >= len(self.last_data.buffer) and (
                buffer[:self.last_data.index] >=
                self.last_data.buffer[:self.last_data.index])
        ):
            return False
        data = TestData.for_buffer(buffer[:self.last_data.index])
        self.test_function(data)
        data.freeze()
        if data.status >= self.last_data.status:
            debug_report('%d bytes %r -> %r, %s' % (
                data.index,
                list(data.buffer[:data.index]), data.status,
                data.output,
            ))
        if self.consider_new_test_data(data):
            if self.last_data.status == Status.INTERESTING:
                self.shrinks += 1
                self.last_data = data
                if self.shrinks >= self.settings.max_shrinks:
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
            debug_report(
                'Run complete after %d examples (%d valid) and %d shrinks' % (
                    self.iterations, self.valid_examples, self.shrinks,
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
            return bytes(buf)

        def draw_zero(data, n, distribution):
            return bytes(n)

        def draw_constant(data, n, distribution):
            return bytes([
                self.random.randint(0, 255)
            ] * n)

        options = [
            draw_new,
            reuse_existing, reuse_existing,
            draw_existing, draw_smaller, draw_larger,
            flip_bit, draw_zero, draw_constant,
        ]

        bits = [
            self.random.choice(options) for _ in range(3)
        ]

        def draw_mutated(data, n, distribution):
            if (
                data.index + n > len(self.last_data.buffer)
            ):
                return distribution(self.random, n)
            return self.random.choice(bits)(data, n, distribution)
        return draw_mutated

    def _run(self):
        self.new_buffer()
        mutations = 0
        start_time = time.time()
        mutator = self._new_mutator()
        while self.last_data.status != Status.INTERESTING:
            if self.valid_examples >= self.settings.max_examples:
                return
            if self.iterations >= self.settings.max_iterations:
                return
            if (
                self.settings.timeout > 0 and
                time.time() >= start_time + self.settings.timeout
            ):
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
                if data.status >= self.last_data.status:
                    self.last_data = data
                    if data.status > self.last_data.status:
                        mutations = 0
                else:
                    mutator = self._new_mutator()

            mutations += 1

        if self.settings.max_shrinks <= 0:
            return

        if not self.last_data.buffer:
            return

        data = TestData.for_buffer(self.last_data.buffer)
        self.test_function(data)
        if data.status != Status.INTERESTING:
            return

        change_counter = -1
        discarding_works = True

        while self.changed > change_counter:
            change_counter = self.changed

            i = 0
            while i < len(self.last_data.intervals):
                u, v = self.last_data.intervals[i]
                if not self.incorporate_new_buffer(
                    self.last_data.buffer[:u] +
                    self.last_data.buffer[v:]
                ):
                    i += 1

            if discarding_works:
                for _ in range(100):
                    if self.incorporate_new_buffer(bytes(
                        b for b in self.last_data.buffer
                        if self.random.randint(0, 2)
                    )):
                        break
                else:
                    discarding_works = False

            from hypothesis.internal.conjecture.minimizer import minimize
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

            block_counter = -1
            while block_counter < self.changed:
                block_counter = self.changed
                blocks = [
                    k for k, v in
                    Counter(
                        self.last_data.buffer[u:v]
                        for u, v in self.last_data.blocks).items()
                    if v > 1
                ]
                for block in blocks:
                    parts = self.last_data.buffer.split(block)
                    assert self.last_data.buffer == block.join(parts)
                    if len(parts) <= 1:
                        continue
                    minimize(
                        block,
                        lambda b: self.incorporate_new_buffer(
                            b.join(parts)),
                        self.random
                    )

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

            i = 0
            alternatives = None
            while i < len(self.last_data.intervals):
                if alternatives is None:
                    alternatives = sorted(set(
                        self.last_data.buffer[u:v]
                        for u, v in self.last_data.intervals), key=len)
                u, v = self.last_data.intervals[i]
                for a in alternatives:
                    if len(a) < v - u:
                        if self.incorporate_new_buffer(
                            self.last_data.buffer[:u] + a +
                            self.last_data.buffer[v:]
                        ):
                            alternatives = None
                            break
                    else:
                        break
                i += 1

    def mutate_data_to_new_buffer(self):
        n = min(len(self.last_data.buffer), self.last_data.index)
        if not n:
            return b''
        if n == 1:
            return self.rand_bytes(1)

        if self.last_data.status == Status.OVERRUN:
            result = bytearray(self.last_data.buffer)
            for i, c in enumerate(self.last_data.buffer):
                t = self.random.randint(0, 2)
                if t == 0:
                    result[i] = 0
                elif t == 1:
                    result[i] = self.random.randint(0, c)
                else:
                    result[i] = c
            return bytes(result)

        probe = self.random.randint(0, 255)
        if probe <= 100 or len(self.last_data.intervals) <= 1:
            c = self.random.randint(0, 2)
            i = self.random.randint(0, self.last_data.index - 1)
            result = bytearray(self.last_data.buffer)
            if c == 0:
                result[i] ^= (1 << self.random.randint(0, 7))
            elif c == 1:
                result[i] = 0
            else:
                result[i] = 255
            return bytes(result)
        else:
            int1 = None
            int2 = None
            while int1 == int2:
                i = self.random.randint(0, len(self.last_data.intervals) - 2)
                int1 = self.last_data.intervals[i]
                int2 = self.last_data.intervals[
                    self.random.randint(
                        i + 1, len(self.last_data.intervals) - 1)]
            return self.last_data.buffer[:int1[0]] + \
                self.last_data.buffer[int2[0]:int2[1]] + \
                self.last_data.buffer[int1[1]:]

    def rand_bytes(self, n):
        if n == 0:
            return b''
        return self.random.getrandbits(n * 8).to_bytes(n, 'big')


def find_interesting_buffer(test_function, settings=None):
    runner = TestRunner(test_function, settings)
    runner.run()
    if runner.last_data.status == Status.INTERESTING:
        return runner.last_data.buffer


def _byte_shrinks(n):
    if n == 0:
        return []
    if n == 1:
        return [0]
    parts = {0, n - 1}
    for i in range(8):
        mask = 1 << i
        if n & mask:
            parts.add(n ^ mask)
    return sorted(parts)


def _draw_predecessor(rnd, xs):
    r = bytearray()
    any_strict = False
    for x in xs:
        if not any_strict:
            c = rnd.randint(0, x)
            if c < x:
                any_strict = True
        else:
            c = rnd.randint(0, 255)
        r.append(c)
    return bytes(r)


def _draw_successor(rnd, xs):
    r = bytearray()
    any_strict = False
    for x in xs:
        if not any_strict:
            c = rnd.randint(x, 255)
            if c > x:
                any_strict = True
        else:
            c = rnd.randint(0, 255)
        r.append(c)
    return bytes(r)


def in_order(x, y):
    return x + y <= y + x
