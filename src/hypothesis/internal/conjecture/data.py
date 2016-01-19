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

from enum import IntEnum

from hypothesis.errors import Frozen
from hypothesis.internal.compat import text_type, binary_type


def uniform(random, n):
    if n == 0:
        return b''
    return random.getrandbits(n * 8).to_bytes(n, 'big')


class Status(IntEnum):
    OVERRUN = 0
    INVALID = 1
    VALID = 2
    INTERESTING = 3


class StopTest(BaseException):

    def __init__(self, data):
        super(StopTest, self).__init__()
        self.data = data


class TestData(object):

    @classmethod
    def for_buffer(self, buffer, expand=False):
        if expand:
            from random import Random
            rnd = Random(buffer)

            def db(data, n, distribution):
                if data.index + n <= len(buffer):
                    return buffer[data.index:data.index + n]
                else:
                    return distribution(rnd, n)

            return TestData(
                max_length=2 ** 64,
                draw_bytes=db
            )
        else:
            return TestData(
                max_length=len(buffer),
                draw_bytes=lambda data, n, distribution:
                buffer[data.index:data.index + n]
            )

    def __init__(self, max_length, draw_bytes):
        self.max_length = max_length
        self._draw_bytes = draw_bytes

        self.block_starts = {}
        self.buffer = bytearray()
        self.output = bytearray()
        self.status = Status.VALID
        self.frozen = False
        self.intervals = []
        self.interval_stack = []

    def __assert_not_frozen(self, name):
        if self.frozen:
            raise Frozen(
                'Cannot call %s on frozen TestData' % (
                    name,))

    @property
    def index(self):
        return len(self.buffer)

    def note(self, value):
        self.__assert_not_frozen('note')
        if not isinstance(value, (text_type, binary_type)):
            value = repr(value)
        if isinstance(value, text_type):
            value = value.encode('utf-8')
        assert isinstance(value, binary_type)
        self.output.extend(value)

    def draw(self, strategy):
        self.start_example()
        result = strategy.do_draw(self)
        self.stop_example()
        return result

    def start_example(self):
        self.__assert_not_frozen('start_example')
        self.interval_stack.append(self.index)

    def stop_example(self):
        self.__assert_not_frozen('stop_example')
        k = self.interval_stack.pop()
        if k != self.index:
            t = (k, self.index)
            if not self.intervals or self.intervals[-1] != t:
                self.intervals.append(t)

    def freeze(self):
        if self.frozen:
            return
        self.frozen = True
        # Intervals are sorted as longest first, then by interval start.
        self.intervals.sort(
            key=lambda se: (se[0] - se[1], se[0])
        )
        self.buffer = bytes(self.buffer)
        del self._draw_bytes

    def draw_bytes(self, n, distribution=uniform):
        self.__assert_not_frozen('draw_bytes')
        initial = self.index
        if self.index + n > self.max_length:
            self.status = Status.OVERRUN
            self.freeze()
            raise StopTest(self)
        self.block_starts.setdefault(n, []).append(initial)
        result = self._draw_bytes(self, n, distribution)
        assert len(result) == n
        assert self.index == initial
        self.buffer.extend(result)
        self.intervals.append((initial, self.index))
        return result

    def mark_interesting(self):
        self.__assert_not_frozen('mark_interesting')
        if self.status == Status.VALID:
            self.status = Status.INTERESTING
        raise StopTest(self)

    def mark_invalid(self):
        self.__assert_not_frozen('mark_invalid')
        if self.status != Status.OVERRUN:
            self.status = Status.INVALID
        raise StopTest(self)

    @property
    def rejected(self):
        return self.status == Status.INVALID or self.status == Status.OVERRUN
