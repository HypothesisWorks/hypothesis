# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

import sys
from enum import IntEnum

import attr

from hypothesis.errors import Frozen, StopTest, InvalidArgument
from hypothesis.internal.compat import hbytes, hrange, text_type, \
    bit_length, benchmark_time, int_from_bytes, unicode_safe_repr
from hypothesis.internal.coverage import IN_COVERAGE_TESTS
from hypothesis.internal.escalation import mark_for_escalation


class Status(IntEnum):
    OVERRUN = 0
    INVALID = 1
    VALID = 2
    INTERESTING = 3


@attr.s(slots=True)
class Example(object):
    depth = attr.ib()
    label = attr.ib()
    start = attr.ib()
    end = attr.ib(default=None)
    discarded = attr.ib(default=None)

    @property
    def length(self):
        return self.end - self.start


@attr.s(hash=False, cmp=False, slots=True)
class StructuralTag(object):
    label = attr.ib()


STRUCTURAL_TAGS = {}


def structural_tag(label):
    try:
        return STRUCTURAL_TAGS[label]
    except KeyError:
        result = StructuralTag(label)
        STRUCTURAL_TAGS[label] = result
        return result


global_test_counter = 0


MAX_DEPTH = 100


class ConjectureData(object):

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
        self.blocks = []
        self.buffer = bytearray()
        self.output = u''
        self.status = Status.VALID
        self.frozen = False
        global global_test_counter
        self.testcounter = global_test_counter
        global_test_counter += 1
        self.start_time = benchmark_time()
        self.events = set()
        self.forced_indices = set()
        self.capped_indices = {}
        self.interesting_origin = None
        self.tags = set()
        self.draw_times = []
        self.__intervals = None

        self.examples = []
        self.example_stack = []
        self.has_discards = False

        self.start_example()

    def __assert_not_frozen(self, name):
        if self.frozen:
            raise Frozen(
                'Cannot call %s on frozen ConjectureData' % (
                    name,))

    def add_tag(self, tag):
        self.tags.add(tag)

    @property
    def depth(self):
        # We always have a single example wrapping everything. We want to treat
        # that as depth 0 rather than depth 1.
        return self.level - 1

    @property
    def index(self):
        return len(self.buffer)

    def note(self, value):
        self.__assert_not_frozen('note')
        if not isinstance(value, text_type):
            value = unicode_safe_repr(value)
        self.output += value

    def draw(self, strategy, label=None):
        if self.is_find and not strategy.supports_find:
            raise InvalidArgument((
                'Cannot use strategy %r within a call to find (presumably '
                'because it would be invalid after the call had ended).'
            ) % (strategy,))

        if strategy.is_empty:
            self.mark_invalid()

        if self.depth >= MAX_DEPTH:
            self.mark_invalid()

        if self.depth == 0 and not IN_COVERAGE_TESTS:  # pragma: no cover
            original_tracer = sys.gettrace()
            try:
                sys.settrace(None)
                return self.__draw(strategy, label=label)
            finally:
                sys.settrace(original_tracer)
        else:
            return self.__draw(strategy, label=label)

    def __draw(self, strategy, label):
        at_top_level = self.depth == 0
        if label is None:
            label = strategy.label
        self.start_example(label=label)
        try:
            if not at_top_level:
                return strategy.do_draw(self)
            else:
                start_time = benchmark_time()
                try:
                    return strategy.do_draw(self)
                except BaseException as e:
                    mark_for_escalation(e)
                    raise
                finally:
                    self.draw_times.append(benchmark_time() - start_time)
        finally:
            if not self.frozen:
                self.stop_example()

    def start_example(self, label=None):
        self.__assert_not_frozen('start_example')
        self.level += 1
        i = len(self.examples)
        self.examples.append(Example(
            depth=self.depth, label=label, start=self.index))
        self.example_stack.append(i)

    def stop_example(self, discard=False):
        if self.frozen:
            return
        self.level -= 1

        k = self.example_stack.pop()
        ex = self.examples[k]
        ex.end = self.index
        ex.discarded = discard

        if discard:
            self.has_discards = True

    def note_event(self, event):
        self.events.add(event)

    def freeze(self):
        if self.frozen:
            assert isinstance(self.buffer, hbytes)
            return
        self.finish_time = benchmark_time()

        while self.example_stack:
            self.stop_example()

        self.frozen = True

        if self.status >= Status.VALID:
            discards = []
            for ex in self.examples:
                if ex.length == 0:
                    continue
                if discards:
                    u, v = discards[-1]
                    if u <= ex.start <= ex.end <= v:
                        continue
                if ex.discarded:
                    discards.append((ex.start, ex.end))
                    continue
                if ex.label is not None:
                    self.tags.add(structural_tag(ex.label))

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

    def draw_bytes(self, n):
        self.__assert_not_frozen('draw_bytes')
        if n == 0:
            return hbytes(b'')
        self.__check_capacity(n)
        self.start_example()
        result = self._draw_bytes(self, n)
        assert len(result) == n
        self.__write(result)
        self.stop_example()
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
