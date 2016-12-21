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

from enum import IntEnum

from hypothesis.errors import Frozen, InvalidArgument
from hypothesis.internal.compat import hbytes, hrange, text_type, \
    int_to_bytes, benchmark_time, unicode_safe_repr, \
    reasonable_byte_type
from hypothesis.internal.sampler import sampler


def uniform(random, n):
    return int_to_bytes(random.getrandbits(n * 8), n)


class Status(IntEnum):
    OVERRUN = 0
    INVALID = 1
    VALID = 2
    INTERESTING = 3


class StopTest(BaseException):

    def __init__(self, testcounter):
        super(StopTest, self).__init__(repr(testcounter))
        self.testcounter = testcounter


global_test_counter = 0

BYTES_TO_STRINGS = [hbytes([b]) for b in range(256)]

UNIFORM_WEIGHTS = (1,) * 256


class ConjectureData(object):

    @classmethod
    def for_buffer(self, buffer):
        return ConjectureData(
            max_length=len(buffer),
            draw_bytes=lambda data, n, distribution:
            buffer[data.index:data.index + n]
        )

    def __init__(self, max_length, draw_bytes):
        self.max_length = max_length
        self.is_find = False
        self._draw_bytes = draw_bytes
        self.overdraw = 0
        self.level = 0
        self.block_starts = {}
        self.blocks = [[0, 0]]
        self.buffer = bytearray()
        self.output = u''
        self.status = Status.VALID
        self.frozen = False
        self.intervals_by_level = []
        self.intervals = []
        self.interval_stack = []
        self.interval_counter_stack = []
        global global_test_counter
        self.testcounter = global_test_counter
        global_test_counter += 1
        self.start_time = benchmark_time()
        self.events = set()
        self.bind_points = set()

    def __block_boundary(self):
        i, j = self.blocks[-1]
        if i == j:
            return
        if not self.interval_stack:
            self.intervals.append(tuple(self.blocks[-1]))
        self.blocks.append([self.index, self.index])

    def __assert_not_frozen(self, name):
        if self.frozen:
            raise Frozen(
                'Cannot call %s on frozen ConjectureData' % (
                    name,))

    @property
    def index(self):
        return len(self.buffer)

    def note(self, value):
        self.__assert_not_frozen('note')
        if not isinstance(value, text_type):
            value = unicode_safe_repr(value)
        self.output += value

    def draw(self, strategy):
        if self.is_find and not strategy.supports_find:
            raise InvalidArgument((
                'Cannot use strategy %r within a call to find (presumably '
                'because it would be invalid after the call had ended).'
            ) % (strategy,))
        self.start_example()
        try:
            return strategy.do_draw(self)
        finally:
            if not self.frozen:
                self.stop_example()

    def mark_bind(self):
        """Marks a point as somewhere that a bind occurs - that is, data
        drawn after this point may depend significantly on data drawn prior
        to this point.

        Having points like this explicitly marked allows for better shrinking,
        as we run a pass which tries to shrink the byte stream prior to a bind
        point while rearranging what comes after somewhat to allow for more
        flexibility. Trying that at every point in the data stream is
        prohibitively expensive, but trying it at a couple dozen is basically
        fine."""
        self.bind_points.add(self.index)

    def start_example(self):
        self.__assert_not_frozen('start_example')
        self.__block_boundary()
        self.interval_stack.append(self.index)
        self.interval_counter_stack.append(len(self.intervals))
        self.level += 1

    def stop_example(self):
        self.__assert_not_frozen('stop_example')
        self.__block_boundary()
        self.level -= 1
        while self.level >= len(self.intervals_by_level):
            self.intervals_by_level.append([])
        k = self.interval_stack.pop()

        if k != self.index:
            t = (k, self.index)
            self.intervals_by_level[self.level].append(t)
            if not self.intervals or self.intervals[-1] != t:
                self.intervals.append(t)

    def note_event(self, event):
        self.events.add(event)

    def freeze(self):
        if self.frozen:
            assert isinstance(self.buffer, hbytes)
            return
        self.frozen = True
        self.blocks = list(map(tuple, self.blocks))
        for i, j in self.blocks:
            self.block_starts.setdefault(j - i, []).append(i)
        self.finish_time = benchmark_time()
        # Intervals are sorted as longest first, then by interval start.
        for l in self.intervals_by_level:
            for i in hrange(len(l) - 1):
                if l[i][1] == l[i + 1][0]:
                    self.intervals.append((l[i][0], l[i + 1][1]))
        self.intervals = sorted(
            set(self.intervals),
            key=lambda se: (se[0] - se[1], se[0])
        )
        self.buffer = hbytes(self.buffer)
        self.events = frozenset(self.events)
        del self._draw_bytes

    def draw_bytes(self, n, distribution=uniform):
        if n == 0:
            return hbytes(b'')
        self.__assert_not_frozen('draw_bytes')
        initial = self.index
        if self.index + n > self.max_length:
            self.overdraw = self.index + n - self.max_length
            self.status = Status.OVERRUN
            self.freeze()
            raise StopTest(self.testcounter)
        result = self._draw_bytes(self, n, distribution)
        if not self.interval_stack:
            self.intervals.append((initial, initial + n))
        assert len(result) == n
        assert self.index == initial
        self.buffer.extend(result)
        self.blocks[-1][-1] += n
        return reasonable_byte_type(result)

    def draw_byte(self, weights=UNIFORM_WEIGHTS):
        weights = tuple(weights)

        s = sampler(weights)

        def distribution(random, n):
            assert n == 1, n
            return BYTES_TO_STRINGS[s.sample(random)]
        result = self.draw_bytes(1, distribution)[0]
        if result < len(weights) and weights[result] > 0:
            return result
        else:
            self.mark_invalid()

    def draw_from_grammar(self, grammar):
        self.start_example()
        result = bytearray()

        weights = [0] * 256

        while True:
            if not grammar.initial_values():
                # We can get into circumstances where we've gone astray because
                # of intersection grammars. In that case there's nothing we
                # can do but abort the test or try again from the beginning.
                if not grammar.matches_empty:
                    self.mark_invalid()
                break
            if grammar.matches_empty:
                p = 0.5
                if not self.draw_byte([p, 1 - p]):
                    break
            values = grammar.initial_values()
            for i in range(256):
                weights[i] = int(i in values)
            c = self.draw_byte(weights)
            grammar = grammar.derivative(c)
            result.append(c)
        self.stop_example()
        return reasonable_byte_type(result)

    def mark_interesting(self):
        self.__assert_not_frozen('mark_interesting')
        self.status = Status.INTERESTING
        self.freeze()
        raise StopTest(self.testcounter)

    def mark_invalid(self):
        self.__assert_not_frozen('mark_invalid')
        self.status = Status.INVALID
        self.freeze()
        raise StopTest(self.testcounter)
