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

import math
import struct
from collections import namedtuple

import hypothesis.internal.conjecture.utils as d
from hypothesis.control import assume
from hypothesis.internal.floats import sign
from hypothesis.searchstrategy.strategies import SearchStrategy, \
    MappedSearchStrategy


class IntStrategy(SearchStrategy):

    """A generic strategy for integer types that provides the basic methods
    other than produce.

    Subclasses should provide the produce method.

    """


class IntegersFromStrategy(SearchStrategy):

    def __init__(self, lower_bound, average_size=100000.0):
        super(IntegersFromStrategy, self).__init__()
        self.lower_bound = lower_bound
        self.average_size = average_size

    def __repr__(self):
        return 'IntegersFromStrategy(%d)' % (self.lower_bound,)

    def do_draw(self, data):
        return self.lower_bound + d.geometric(data, 1.0 / self.average_size)


class RandomGeometricIntStrategy(IntStrategy):

    """A strategy that produces integers whose magnitudes are a geometric
    distribution and whose sign is randomized with some probability.

    It will tend to be biased towards mostly negative or mostly
    positive, and the size of the integers tends to be biased towards
    the small.

    """

    def __repr__(self):
        return 'RandomGeometricIntStrategy()'

    def do_draw(self, data):
        return d.n_byte_signed(data, d.integer_range(data, 0, 8))


class WideRangeIntStrategy(IntStrategy):

    def __repr__(self):
        return 'WideRangeIntStrategy()'

    def do_draw(self, data):
        size = 16

        def distribution(random, n):
            assert n == size
            k = min(
                random.randint(0, n * 8 - 1),
                random.randint(0, n * 8 - 1),
            )
            if k > 0:
                r = random.getrandbits(k)
            else:
                r = 0
            if random.randint(0, 1):
                r = -r
            return r.to_bytes(n, 'big', signed=True)
        negative = data.draw_bytes(1)[0] & 1
        byt = data.draw_bytes(size, distribution=distribution)
        r = int.from_bytes(byt, 'big', signed=False)
        if negative:
            r = -r
        return r


class BoundedIntStrategy(SearchStrategy):

    """A strategy for providing integers in some interval with inclusive
    endpoints."""

    def __init__(self, start, end):
        SearchStrategy.__init__(self)
        self.start = start
        self.end = end
        if start > end:
            raise ValueError(u'Invalid range [%d, %d]' % (start, end))

    def __repr__(self):
        return 'BoundedIntStrategy(%d, %d)' % (self.start, self.end)

    def do_draw(self, data):
        return d.integer_range(data, self.start, self.end)


def is_integral(value):
    try:
        return int(value) == value
    except (OverflowError, ValueError):
        return False

NASTY_FLOATS = [
    0.0, 0.5, 1.0 / 3, 10e6, 10e-6, 1.175494351e-38, 2.2250738585072014e-308,
    1.7976931348623157e+308, 3.402823466e+38, 9007199254740992, 1 - 10e-6,
    2 + 10e-6, 1.192092896e-07, 2.2204460492503131e-016,
    float('inf'), float('nan'),
]
NASTY_FLOATS.extend([-x for x in NASTY_FLOATS])
assert len(NASTY_FLOATS) == 32
INFINITY = float('inf')


class FloatStrategy(SearchStrategy):

    """Generic superclass for strategies which produce floats."""

    def __init__(self, allow_infinity, allow_nan):
        SearchStrategy.__init__(self)
        assert isinstance(allow_infinity, bool)
        assert isinstance(allow_nan, bool)
        self.allow_infinity = allow_infinity
        self.allow_nan = allow_nan

    def __repr__(self):
        return '%s()' % (self.__class__.__name__,)

    def permitted(self, f):
        if not self.allow_infinity and math.isinf(f):
            return False
        if not self.allow_nan and math.isnan(f):
            return False
        return True

    def do_draw(self, data):
        def draw_float_bytes(random, n):
            assert n == 8
            while True:
                i = random.randint(1, 10)
                if i <= 4:
                    f = random.choice(NASTY_FLOATS)
                    if self.permitted(f):
                        return struct.pack(b'!d', f)
                else:
                    return bytes(random.randint(0, 255) for _ in range(8))
        result = struct.unpack(b'!d', data.draw_bytes(8, draw_float_bytes))[0]
        assume(self.permitted(result))
        return result


def float_order_key(k):
    return (sign(k), k)


class FixedBoundedFloatStrategy(SearchStrategy):

    """A strategy for floats distributed between two endpoints.

    The conditional distribution tries to produce values clustered
    closer to one of the ends.

    """
    Parameter = namedtuple(
        'Parameter',
        ('cut', 'leftwards')
    )

    def __init__(self, lower_bound, upper_bound):
        SearchStrategy.__init__(self)
        self.lower_bound = float(lower_bound)
        self.upper_bound = float(upper_bound)
        lb = float_order_key(self.lower_bound)
        ub = float_order_key(self.upper_bound)

        self.zeroes = [
            z for z in (-0.0, 0.0)
            if lb <= float_order_key(z) <= ub
        ]

    def __repr__(self):
        return 'FixedBoundedFloatStrategy(%s, %s)' % (
            self.lower_bound, self.upper_bound,
        )

    def do_draw(self, data):
        def draw_float_bytes(random, n):
            assert n == 8
            i = random.randint(0, 9)
            if i == 0:
                f = self.lower_bound
            elif i == 1:
                f = self.upper_bound
            elif i == 2 and self.zeroes:
                f = random.choice(self.zeroes)
            else:
                f = random.random() * (
                    self.upper_bound - self.lower_bound
                ) + self.lower_bound
            return struct.pack(b'!d', f)
        f = struct.unpack(b'!d', data.draw_bytes(8, draw_float_bytes))[0]
        assume(self.lower_bound <= f <= self.upper_bound)
        assume(sign(self.lower_bound) <= sign(f) <= sign(self.upper_bound))
        return f


class ComplexStrategy(MappedSearchStrategy):

    """A strategy over complex numbers, with real and imaginary values
    distributed according to some provided strategy for floating point
    numbers."""

    def __repr__(self):
        return 'ComplexStrategy()'

    def pack(self, value):
        return complex(*value)
