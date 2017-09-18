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

from enum import IntEnum
from array import array

from hypothesis.errors import Frozen, InvalidArgument
from hypothesis.internal.compat import hbytes, hrange, text_type, \
    bit_length, benchmark_time, int_from_bytes, unicode_safe_repr


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


MAX_DEPTH = 100


class Blocks(object):
    __slots__ = ('contents',)

    def __init__(self):
        self.contents = array('H')

    def append(self, v):
        assert len(v) == 2
        self.contents.extend(v)

    def __len__(self):
        return len(self.contents) // 2

    def __getitem__(self, i):
        return (self.contents[i * 2], self.contents[i * 2 + 1])


class ConjectureData(object):
    __slots__ = (
        'max_length',
        'is_find',
        '_draw_bytes',
        'overdraw',
        'level',
        'block_starts',
        'blocks',
        'buffer',
        'output',
        'status',
        'frozen',
        'intervals_by_level',
        'intervals',
        'interval_stack',
        'testcounter',
        'start_time',
        'events',
        'forced_indices',
        'capped_indices',
        'interesting_origin',
        'finish_time',
        'current_node_index',
        'hit_novelty',
        'evaluated_to',
        'hit_zero_bound',
        '_hypothesis_shared_strategies',
        'expected_exception',
    )

    @classmethod
    def for_buffer(self, buffer):
        buffer = hbytes(buffer)
        return ConjectureData(
            max_length=len(buffer),
            draw_bytes=lambda data, n:
            hbytes(buffer[data.index:data.index + n])
        )

    def __init__(self, max_length, draw_bytes):
        self.max_length = max_length
        self.is_find = False
        self._draw_bytes = draw_bytes
        self.overdraw = 0
        self.level = 0
        self.block_starts = {}
        self.blocks = Blocks()
        self.buffer = bytearray()
        self.output = u''
        self.status = Status.VALID
        self.frozen = False
        self.intervals_by_level = []
        self.intervals = []
        self.interval_stack = []
        global global_test_counter
        self.testcounter = global_test_counter
        global_test_counter += 1
        self.start_time = benchmark_time()
        self.events = set()
        self.forced_indices = set()
        self.capped_indices = {}
        self.interesting_origin = None

    def __assert_not_frozen(self, name):
        if self.frozen:
            raise Frozen(
                'Cannot call %s on frozen ConjectureData' % (
                    name,))

    @property
    def depth(self):
        return len(self.interval_stack)

    @property
    def index(self):
        return len(self.buffer)

    def note(self, value):
        self.__assert_not_frozen('note')
        if not isinstance(value, text_type):
            value = unicode_safe_repr(value)
        self.output += value

    def draw(self, strategy):
        if self.depth >= MAX_DEPTH:
            self.mark_invalid()
        if strategy.is_empty:
            self.mark_invalid()

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

    def start_example(self):
        self.__assert_not_frozen('start_example')
        self.interval_stack.append(self.index)
        self.level += 1

    def stop_example(self):
        if self.frozen:
            return
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
        self.finish_time = benchmark_time()
        # Intervals are sorted as longest first, then by interval start.
        for l in self.intervals_by_level:
            for i in hrange(len(l) - 1):
                if l[i][1] == l[i + 1][0]:
                    self.intervals.append((l[i][0], l[i + 1][1]))
        del self.intervals_by_level
        self.intervals = sorted(
            set(self.intervals),
            key=lambda se: (se[0] - se[1], se[0])
        )
        self.buffer = hbytes(self.buffer)
        self.events = frozenset(self.events)
        del self._draw_bytes

    def draw_bits(self, n):
        self.__assert_not_frozen('draw_bits')
        if n == 0:
            result = 0
        elif n % 8 == 0:
            return int_from_bytes(self.draw_bytes(n // 8))
        else:
            n_bytes = (n // 8) + 1
            self.__check_capacity(n_bytes)
            buf = bytearray(self._draw_bytes(self, n_bytes))
            assert len(buf) == n_bytes
            mask = (1 << (n % 8)) - 1
            buf[0] &= mask
            self.capped_indices[self.index] = mask
            buf = hbytes(buf)
            self.__write(buf)
            result = int_from_bytes(buf)
        assert bit_length(result) <= n
        return result

    def write(self, string):
        self.__assert_not_frozen('write')
        self.__check_capacity(len(string))
        assert isinstance(string, hbytes)
        original = self.index
        self.__write(string)
        self.forced_indices.update(hrange(original, self.index))
        return string

    def __check_capacity(self, n):
        if self.index + n > self.max_length:
            self.overdraw = self.index + n - self.max_length
            self.status = Status.OVERRUN
            self.freeze()
            raise StopTest(self.testcounter)

    def __write(self, result):
        initial = self.index
        n = len(result)
        self.block_starts.setdefault(n, []).append(initial)
        self.blocks.append((initial, initial + n))
        assert len(result) == n
        assert self.index == initial
        self.buffer.extend(result)
        self.intervals.append((initial, self.index))

    def draw_bytes(self, n):
        self.__assert_not_frozen('draw_bytes')
        if n == 0:
            return hbytes(b'')
        self.__check_capacity(n)
        result = self._draw_bytes(self, n)
        assert len(result) == n
        self.__write(result)
        return hbytes(result)

    def mark_interesting(self, interesting_origin=None):
        self.__assert_not_frozen('mark_interesting')
        self.interesting_origin = interesting_origin
        self.status = Status.INTERESTING
        self.freeze()
        raise StopTest(self.testcounter)

    def mark_invalid(self):
        self.__assert_not_frozen('mark_invalid')
        self.status = Status.INVALID
        self.freeze()
        raise StopTest(self.testcounter)
