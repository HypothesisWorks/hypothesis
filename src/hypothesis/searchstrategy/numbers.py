# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import sys
import math
import struct
from random import Random
from collections import namedtuple

import hypothesis.specifiers as specifiers
import hypothesis.internal.distributions as dist
from hypothesis.internal.compat import hrange, integer_types
from hypothesis.searchstrategy.misc import SampledFromStrategy
from hypothesis.searchstrategy.strategies import BadData, SearchStrategy, \
    MappedSearchStrategy, strategy, check_type, check_data_type


class IntStrategy(SearchStrategy):

    """A generic strategy for integer types that provides the basic methods
    other than produce.

    Subclasses should provide the produce method.

    """

    def from_basic(self, data):
        check_data_type(integer_types, data)
        return data

    def to_basic(self, template):
        return template

    def reify(self, template):
        return template

    def simplify(self, x):
        ix = int(x)
        if type(ix) != type(x):  # pragma: no cover
            yield ix
        if x < 0:
            yield -x
            for y in self.simplify(-x):
                yield -y
        elif x > 0:
            yield 0
            if x == 1:
                return
            yield x // 2
            if x == 2:
                return
            max_iters = 100
            if x <= max_iters:
                for i in hrange(x - 1, 0, -1):
                    if i != x // 2:
                        yield i
            else:
                random = Random(x)
                seen = {0, x // 2}
                for _ in hrange(max_iters):
                    i = random.randint(0, x - 1)
                    if i not in seen:
                        yield i
                    seen.add(i)


class RandomGeometricIntStrategy(IntStrategy):

    """A strategy that produces integers whose magnitudes are a geometric
    distribution and whose sign is randomized with some probability.

    It will tend to be biased towards mostly negative or mostly
    positive, and the size of the integers tends to be biased towards
    the small.

    """
    Parameter = namedtuple(
        'Parameter',
        ('negative_probability', 'p')
    )

    def __repr__(self):
        return 'RandomGeometricIntStrategy()'

    def produce_parameter(self, random):
        return self.Parameter(
            negative_probability=random.betavariate(0.5, 0.5),
            p=random.betavariate(0.2, 1.8),
        )

    def produce_template(self, context, parameter):
        value = dist.geometric(context.random, parameter.p)
        if dist.biased_coin(context.random, parameter.negative_probability):
            value = -value
        return value


class BoundedIntStrategy(SearchStrategy):

    """A strategy for providing integers in some interval with inclusive
    endpoints."""

    def __init__(self, start, end):
        SearchStrategy.__init__(self)
        self.start = start
        self.end = end
        if start > end:
            raise ValueError('Invalid range [%d, %d]' % (start, end))
        self.size_lower_bound = end - start + 1
        self.size_upper_bound = end - start + 1

    def __repr__(self):
        return 'BoundedIntStrategy(%d, %d)' % (self.start, self.end)

    def produce_parameter(self, random):
        return dist.non_empty_subset(
            random,
            tuple(range(self.start, self.end + 1)),
            activation_chance=min(0.5, 3.0 / (self.end - self.start + 1))
        )

    def from_basic(self, data):
        check_data_type(integer_types, data)
        return data

    def to_basic(self, template):
        return template

    def reify(self, value):
        return value

    def produce_template(self, context, parameter):
        if self.start == self.end:
            return self.start
        return context.random.choice(parameter)

    def simplify(self, x):
        if x == self.start:
            return
        mid = (self.start + self.end) // 2
        for t in hrange(self.start, min(x, mid)):
            yield t
        if x > mid:
            yield self.start + (self.end - x)
            for t in hrange(self.end, x, -1):
                yield t


class FloatStrategy(SearchStrategy):

    """Generic superclass for strategies which produce floats."""

    def __init__(self):
        SearchStrategy.__init__(self)
        self.int_strategy = RandomGeometricIntStrategy()

    def __repr__(self):
        return '%s()' % (self.__class__.__name__,)

    def to_basic(self, value):
        check_type(float, value)
        return (
            struct.unpack(b'!Q', struct.pack(b'!d', value))[0]
        )

    def from_basic(self, value):
        check_type(integer_types, value)
        try:
            return (
                struct.unpack(b'!d', struct.pack(b'!Q', value))[0]
            )
        except (struct.error, ValueError, OverflowError) as e:
            raise BadData(e.args[0])

    def reify(self, value):
        return value

    def simplify(self, x):
        if x == 0.0:
            return
        if math.isnan(x):
            yield 0.0
            yield float('inf')
            yield -float('inf')
            return
        if math.isinf(x):
            yield math.copysign(
                sys.float_info.max, x
            )
            return

        if x < 0:
            yield -x

        yield 0.0
        try:
            n = int(x)
            y = float(n)
            if x != y:
                yield y
            for m in self.int_strategy.simplify(n):
                yield x + (m - n)
        except (ValueError, OverflowError):
            pass
        if abs(x) > 1.0:
            yield x / 2


class WrapperFloatStrategy(FloatStrategy):

    def __init__(self, sub_strategy):
        super(WrapperFloatStrategy, self).__init__()
        self.sub_strategy = sub_strategy

    def __repr__(self):
        return 'WrapperFloatStrategy(%r)' % (self.sub_strategy,)

    def produce_parameter(self, random):
        return self.sub_strategy.produce_parameter(random)

    def produce_template(self, context, pv):
        return self.sub_strategy.reify(
            self.sub_strategy.produce_template(context, pv))


class JustIntFloats(FloatStrategy):

    def __init__(self, int_strategy):
        super(JustIntFloats, self).__init__()
        self.int_strategy = int_strategy

    def produce_parameter(self, random):
        return self.int_strategy.draw_parameter(random)

    def produce_template(self, context, pv):
        return float(self.int_strategy.draw_template(context, pv))


def compose_float(sign, exponent, fraction):
    as_long = (sign << 63) | (exponent << 52) | fraction
    return struct.unpack(b'!d', struct.pack(b'!Q', as_long))[0]


class FullRangeFloats(FloatStrategy):

    Parameter = namedtuple(
        'Parameter',
        ('negative_probability', 'subnormal_probability')
    )

    def produce_parameter(self, random):
        return self.Parameter(
            negative_probability=dist.uniform_float(random, 0, 1),
            subnormal_probability=dist.uniform_float(random, 0, 0.5),
        )

    def produce_template(self, context, pv):
        sign = int(dist.biased_coin(context.random, pv.negative_probability))
        if dist.biased_coin(context.random, pv.subnormal_probability):
            exponent = 0
        else:
            exponent = context.random.getrandbits(11)

        return compose_float(
            sign,
            exponent,
            context.random.getrandbits(52)
        )


def _find_max_exponent():
    """Returns the largest n such that math.ldexp(1.0, -n) > 0"""
    upper = 1
    while math.ldexp(1.0, -upper) > 0:
        lower = upper
        upper *= 2
    assert math.ldexp(1.0, -lower) > 0
    assert math.ldexp(1.0, -upper) == 0
    assert upper > lower + 1
    while upper > lower + 1:
        mid = (upper + lower) // 2
        if math.ldexp(1.0, -mid) > 0:
            lower = mid
        else:
            upper = mid
    return lower


class SmallFloats(FloatStrategy):
    max_exponent = _find_max_exponent()
    Parameter = namedtuple(
        'Parameter',
        ('negative_probability', 'min_exponent'),
    )

    def produce_parameter(self, random):
        return self.Parameter(
            negative_probability=dist.uniform_float(random, 0, 1),
            min_exponent=random.randint(0, self.max_exponent)
        )

    def produce_template(self, context, pv):
        base = math.ldexp(
            context.random.random(),
            -context.random.randint(pv.min_exponent, self.max_exponent)
        )
        if dist.biased_coin(context.random, pv.negative_probability):
            base = -base
        return base


class FixedBoundedFloatStrategy(FloatStrategy):

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

    def produce_parameter(self, random):
        return self.Parameter(
            cut=random.random(),
            leftwards=dist.biased_coin(random, 0.5)
        )

    def produce_template(self, context, pv):
        random = context.random
        cut = self.lower_bound + pv.cut * (self.upper_bound - self.lower_bound)
        if pv.leftwards:
            left = self.lower_bound
            right = cut
        else:
            left = cut
            right = self.upper_bound
        return left + random.random() * (right - left)

    def simplify(self, value):
        if value == self.lower_bound:
            return
        yield self.lower_bound
        yield self.upper_bound
        mid = (self.lower_bound + self.upper_bound) * 0.5
        yield mid


class BoundedFloatStrategy(FloatStrategy):

    """A float strategy such that every conditional distribution is bounded but
    the endpoints may be arbitrary."""

    Parameter = namedtuple(
        'Parameter',
        ('left', 'length', 'spread'),
    )

    def __init__(self):
        super(BoundedFloatStrategy, self).__init__()
        self.inner_strategy = FixedBoundedFloatStrategy(0, 1)

    def produce_parameter(self, random):
        return self.Parameter(
            left=random.normalvariate(0, 1),
            length=random.expovariate(1),
            spread=self.inner_strategy.draw_parameter(random),
        )

    def produce_template(self, context, pv):
        return pv.left + self.inner_strategy.draw_template(
            context, pv.spread
        ) * pv.length


class GaussianFloatStrategy(FloatStrategy):

    """A float strategy such that every conditional distribution is drawn from
    a gaussian."""

    def produce_parameter(self, random):
        return random.normalvariate(0, 1)

    def produce_template(self, context, mean):
        return context.random.normalvariate(mean, 1)


class ExponentialFloatStrategy(FloatStrategy):

    """
    A float strategy such that every conditional distribution is of the form
    aX + b where a = +/- 1 and X is an exponentially distributed random
    variable.
    """

    Parameter = namedtuple(
        'Parameter',
        ('lambd', 'zero_point', 'negative'),
    )

    def produce_parameter(self, random):
        return self.Parameter(
            lambd=random.gammavariate(2, 50),
            zero_point=random.normalvariate(0, 1),
            negative=dist.biased_coin(random, 0.5),
        )

    def produce_template(self, context, pv):
        value = context.random.expovariate(pv.lambd)
        if pv.negative:
            value = -value
        return pv.zero_point + value


class NastyFloats(FloatStrategy, SampledFromStrategy):

    def __init__(self):
        SampledFromStrategy.__init__(
            self,
            elements=[
                0.0,
                sys.float_info.min,
                -sys.float_info.min,
                float('inf'),
                -float('inf'),
                float('nan'),
            ]
        )

    def reify(self, value):
        return SampledFromStrategy.reify(self, value)


class ComplexStrategy(MappedSearchStrategy):

    """A strategy over complex numbers, with real and imaginary values
    distributed according to some provided strategy for floating point
    numbers."""

    def __repr__(self):
        return 'ComplexStrategy()'

    def pack(self, value):
        return complex(*value)


@strategy.extend(specifiers.IntegerRange)
def define_stragy_for_integer_Range(specifier, settings):
    return BoundedIntStrategy(specifier.start, specifier.end)


@strategy.extend(specifiers.FloatRange)
def define_strategy_for_float_Range(specifier, settings):
    return FixedBoundedFloatStrategy(specifier.start, specifier.end)


@strategy.extend_static(int)
def int_strategy(specifier, settings):
    return RandomGeometricIntStrategy()


@strategy.extend_static(float)
def define_float_strategy(specifier, settings):
    return WrapperFloatStrategy(
        GaussianFloatStrategy() |
        BoundedFloatStrategy() |
        ExponentialFloatStrategy() |
        JustIntFloats(strategy(int)) |
        NastyFloats() |
        NastyFloats() |
        FullRangeFloats() |
        SmallFloats()
    )


@strategy.extend_static(complex)
def define_complex_strategy(specifier, settings):
    return ComplexStrategy(strategy((float, float), settings))
