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

from enum import IntEnum

import attr

from hypothesis.errors import Frozen, StopTest, InvalidArgument
from hypothesis.internal.compat import hbytes, hrange, text_type, \
    bit_length, benchmark_time, int_from_bytes, unicode_safe_repr
from hypothesis.internal.escalation import mark_for_escalation
from hypothesis.internal.conjecture.utils import calc_label_from_name

TOP_LABEL = calc_label_from_name('top')
DRAW_BYTES_LABEL = calc_label_from_name('draw_bytes() in ConjectureData')


class Status(IntEnum):
    OVERRUN = 0
    INVALID = 1
    VALID = 2
    INTERESTING = 3

    def __repr__(self):
        return 'Status.%s' % (self.name,)


@attr.s(slots=True)
class Example(object):
    depth = attr.ib()
    label = attr.ib()
    index = attr.ib()
    start = attr.ib()
    end = attr.ib(default=None)

    # An example is "trivial" if it only contains forced bytes and zero bytes.
    # All examples start out as trivial, and then get marked non-trivial when
    # we see a byte that is neither forced nor zero.
    trivial = attr.ib(default=True)
    discarded = attr.ib(default=None)
    children = attr.ib(default=attr.Factory(list))

    @property
    def length(self):
        return self.end - self.start


@attr.s(slots=True, frozen=True)
class Block(object):
    start = attr.ib()
    end = attr.ib()
    index = attr.ib()

    forced = attr.ib()
    all_zero = attr.ib()

    @property
    def bounds(self):
        return (self.start, self.end)

    @property
    def length(self):
        return self.end - self.start

    @property
    def trivial(self):
        return self.forced or self.all_zero


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
        self.masked_indices = {}
        self.interesting_origin = None
        self.draw_times = []
        self.max_depth = 0

        self.examples = []
        self.example_stack = []
        self.has_discards = False

        self.start_example(TOP_LABEL)

    def __assert_not_frozen(self, name):
        if self.frozen:
            raise Frozen(
                'Cannot call %s on frozen ConjectureData' % (
                    name,))

    @property
    def depth(self):
        # We always have a single example wrapping everything. We want to treat
        # that as depth 0 rather than depth 1.
        return len(self.example_stack) - 1

    @property
    def index(self):
        return len(self.buffer)

    def all_block_bounds(self):
        return [block.bounds for block in self.blocks]

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
            self.stop_example()

    def start_example(self, label):
        self.__assert_not_frozen('start_example')

        i = len(self.examples)
        new_depth = self.depth + 1
        ex = Example(
            index=i,
            depth=new_depth, label=label, start=self.index,
        )
        self.examples.append(ex)
        if self.example_stack:
            p = self.example_stack[-1]
            self.examples[p].children.append(ex)
        self.example_stack.append(i)
        self.max_depth = max(self.max_depth, self.depth)
        return ex

    def stop_example(self, discard=False):
        if self.frozen:
            return

        k = self.example_stack.pop()
        ex = self.examples[k]
        ex.end = self.index

        if self.example_stack and not ex.trivial:
            self.examples[self.example_stack[-1]].trivial = False

        # We don't want to count empty examples as discards even if the flag
        # says we should. This leads to situations like
        # https://github.com/HypothesisWorks/hypothesis/issues/1230
        # where it can look like we should discard data but there's nothing
        # useful for us to do.
        if self.index == ex.start:
            discard = False

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
            self.masked_indices[self.index] = mask
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
        self.__write(string, forced=True)
        self.forced_indices.update(hrange(original, self.index))
        return string

    def __check_capacity(self, n):
        if self.index + n > self.max_length:
            self.overdraw = self.index + n - self.max_length
            self.status = Status.OVERRUN
            self.freeze()
            raise StopTest(self.testcounter)

    def __write(self, result, forced=False):
        ex = self.start_example(DRAW_BYTES_LABEL)
        initial = self.index
        n = len(result)

        block = Block(
            start=initial,
            end=initial + n,
            index=len(self.blocks),
            forced=forced,
            all_zero=not any(result),
        )
        ex.trivial = block.trivial

        self.block_starts.setdefault(n, []).append(block.start)
        self.blocks.append(block)
        assert self.blocks[block.index] is block
        assert len(result) == n
        assert self.index == initial
        self.buffer.extend(result)
        self.stop_example()

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
