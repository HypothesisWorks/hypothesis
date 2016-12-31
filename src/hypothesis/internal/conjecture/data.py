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

import hypothesis.internal._sampler as s
from hypothesis.errors import Frozen, InvalidArgument
from hypothesis.internal.compat import hbytes, hrange, text_type, \
    int_to_bytes, benchmark_time, unicode_safe_repr, \
    reasonable_byte_type


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


def _array_to_pointer(weights):
    return s.ffi.cast("double*", s.ffi.from_buffer(weights))


class Sampler(object):
    def __init__(self, random):
        self.lib = s.lib
        self.__samplers = self.lib.sampler_family_new(
            2048, random.getrandbits(64)
        )

    def sample(self, weights):
        return self.lib.sampler_family_sample(
            self.__samplers, len(weights), _array_to_pointer(weights))

    def __del__(self):
        self.lib.sampler_family_free(self.__samplers)


def draw_random(random):
    sampler = Sampler(random)

    def accept(data, weights, choices):
        return choices[sampler.sample(weights)]
    return accept

ALL_BYTES = tuple(hrange(256))


class ConjectureData(object):

    @classmethod
    def for_buffer(self, buffer):
        return ConjectureData(
            max_length=len(buffer),
            draw_byte=lambda data, weights, choices: buffer[data.index],
        )

    @classmethod
    def for_random(self, random, max_length):
        return ConjectureData(
            max_length=max_length,
            draw_byte=draw_random(random),
        )

    def __init__(self, max_length, draw_byte):
        self.max_length = max_length
        self.is_find = False
        self._draw_byte = draw_byte
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
        self.weights = []
        self.choices = []

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
        assert len(self.weights) == len(self.buffer) == len(self.choices)
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
        del self._draw_byte

    def draw_byte(self, weights=UNIFORM_WEIGHTS, choices=None):
        if self.index >= self.max_length:
            self.overdraw = 1
            self.status = Status.OVERRUN
            self.freeze()
            raise StopTest(self.testcounter)

        if choices is not None:
            assert len(choices) == len(weights)
        else:
            choices = ALL_BYTES

        result = self._draw_byte(self, tuple(weights), choices)
        self.buffer.append(result)
        self.weights.append(weights)
        self.choices.append(choices)

        if choices is ALL_BYTES:
            index_of_result = result
        else:
            try:
                index_of_result = choices.index(result)
            except ValueError:
                index_of_result = len(weights)

        if index_of_result >= len(weights):
            weight_of_result = 0
        else:
            weight_of_result = weights[index_of_result]

        if weight_of_result <= 0:
            self.mark_invalid()
        self.blocks[-1][-1] += 1
        return result

    def __draw_prefix(self, result, grammar):
        state = grammar
        while True:
            weights = state.weights()
            if not any(weights):
                assert state.matches_empty
                break
            if state.matches_empty:
                return state
            c = self.draw_byte(weights, state.choices())
            state = state.derivative(c)
            if not state.has_matches():
                self.mark_invalid()
            result.append(c)

    def draw_from_grammar(self, grammar):
        if not grammar.has_matches():
            self.mark_invalid()
        result = bytearray()

        state = grammar
        while True:
            assert state.has_matches()
            state = self.__draw_prefix(result, state)
            if state is None:
                break
            assert state.matches_empty
            p = 0.5
            if not self.draw_byte([p, 1 - p]):
                break
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
