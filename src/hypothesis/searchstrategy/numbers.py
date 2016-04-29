# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

import math
import struct
from collections import namedtuple

import hypothesis.internal.conjecture.utils as d
from hypothesis.control import assume
from hypothesis.internal.compat import int_to_bytes, int_from_bytes, \
    bytes_from_list
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
        return int(
            self.lower_bound + d.geometric(data, 1.0 / self.average_size))


class WideRangeIntStrategy(IntStrategy):

    def __repr__(self):
        return 'WideRangeIntStrategy()'

    def do_draw(self, data):
        size = 16
        sign_mask = 2 ** (size * 8 - 1)

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
                r |= sign_mask
            else:
                r &= (~sign_mask)
            return int_to_bytes(r, n)
        byt = data.draw_bytes(size, distribution=distribution)
        r = int_from_bytes(byt)
        negative = r & sign_mask
        r &= (~sign_mask)
        if negative:
            r = -r
        return int(r)


class BoundedIntStrategy(SearchStrategy):

    """A strategy for providing integers in some interval with inclusive
    endpoints."""

    def __init__(self, start, end):
        SearchStrategy.__init__(self)
        self.start = start
        self.end = end

    def __repr__(self):
        return 'BoundedIntStrategy(%d, %d)' % (self.start, self.end)

    def do_draw(self, data):
        return d.integer_range(data, self.start, self.end)


NASTY_FLOATS = [
    0.0, 0.5, 1.0 / 3, 10e6, 10e-6, 1.175494351e-38, 2.2250738585072014e-308,
    1.7976931348623157e+308, 3.402823466e+38, 9007199254740992, 1 - 10e-6,
    2 + 10e-6, 1.192092896e-07, 2.2204460492503131e-016,

] + [float('inf'), float('nan')] * 5
NASTY_FLOATS.extend([-x for x in NASTY_FLOATS])


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
                elif i == 5:
                    return bytes_from_list(
                        random.randint(0, 255) for _ in range(8))
                elif i == 6:
                    f = random.random() * (
                        random.randint(0, 1) * 2 - 1
                    )
                elif i == 7:
                    f = random.gauss(0, 1)
                elif i == 8:
                    f = float(random.randint(-2 ** 63, 2 ** 63))
                else:
                    f = random.gauss(
                        random.randint(-2 ** 63, 2 ** 63), 1
                    )
                if self.permitted(f):
                    return struct.pack(b'!d', f)
        result = struct.unpack(b'!d', bytes(
            data.draw_bytes(8, draw_float_bytes)))[0]
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

        self.critical = [
            z for z in (-0.0, 0.0)
            if lb <= float_order_key(z) <= ub
        ]
        self.critical.append(self.lower_bound)
        self.critical.append(self.upper_bound)

    def __repr__(self):
        return 'FixedBoundedFloatStrategy(%s, %s)' % (
            self.lower_bound, self.upper_bound,
        )

    def do_draw(self, data):
        def draw_float_bytes(random, n):
            assert n == 8
            i = random.randint(0, 20)
            if i <= 2:
                f = random.choice(self.critical)
            else:
                f = random.random() * (
                    self.upper_bound - self.lower_bound
                ) + self.lower_bound
            return struct.pack(b'!d', f)
        f = struct.unpack(b'!d', bytes(
            data.draw_bytes(8, draw_float_bytes)))[0]
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
