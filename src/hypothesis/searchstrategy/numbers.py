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
from decimal import Decimal
from fractions import Fraction
from collections import namedtuple

import hypothesis.specifiers as specifiers
import hypothesis.internal.distributions as dist
from hypothesis.internal.compat import hrange, text_type, integer_types
from hypothesis.searchstrategy.misc import SampledFromStrategy
from hypothesis.searchstrategy.strategies import EFFECTIVELY_INFINITE, \
    BadData, SearchStrategy, MappedSearchStrategy, strategy, check_type, \
    check_data_type


def integer_or_bad(data):
    check_data_type(text_type, data)
    try:
        return int(data)
    except ValueError:
        raise BadData('Invalid integer %r' % (data,))


class IntStrategy(SearchStrategy):

    """A generic strategy for integer types that provides the basic methods
    other than produce.

    Subclasses should provide the produce method.

    """

    def from_basic(self, data):
        return integer_or_bad(data)

    def to_basic(self, template):
        return text_type(template)

    def simplifiers(self, random, template):
        yield self.try_negate
        yield self.try_small_numbers
        i = 1
        while i < abs(template):
            yield self.try_shrink(i, 2 * i)
            i *= 2

    def reify(self, template):
        return int(template)

    def strictly_simpler(self, x, y):
        if y < 0:
            return x > y
        if y == 0:
            return False
        return 0 <= x < y

    def try_negate(self, random, x):
        if x >= 0:
            return
        yield -x

    def try_small_numbers(self, random, x):
        if x != 0:
            yield 0
        if x > 1:
            yield 1
        if x < -1:
            yield -1

    def try_shrink(self, lo, hi):
        def accept(random, x):
            if x < 0:
                for i in accept(random, -x):
                    yield -i
            if x <= lo:
                return

            lb = lo
            while True:
                yield lb
                new_lb = (lb + x) // 2
                if new_lb <= lb or new_lb >= hi:
                    return
                if new_lb > lb + 2:
                    yield random.randint(lb + 1, new_lb - 1)
                lb = new_lb
        accept.__name__ = str(
            'try_shrink(%d, %d)' % (lo, hi)
        )
        return accept


class IntegersFromStrategy(SearchStrategy):

    def __init__(self, lower_bound, average_size=100.0):
        super(IntegersFromStrategy, self).__init__()
        self.lower_bound = lower_bound
        self.average_size = average_size

    def __repr__(self):
        return 'IntegersFromStrategy(%d)' % (self.lower_bound,)

    def produce_parameter(self, random):
        return random.random() * 2 / self.average_size

    def produce_template(self, context, parameter):
        return self.lower_bound + dist.geometric(context.random, parameter)

    def reify(self, template):
        return template

    def try_shrink(self, i):
        lo = self.lower_bound + i
        hi = self.lower_bound + 2 * i

        def accept(random, x):
            if x <= lo:
                return

            lb = lo
            while True:
                yield lb
                new_lb = (lb + x) // 2
                if new_lb <= lb or new_lb >= hi:
                    return
                if new_lb > lb + 2:
                    yield random.randint(lb + 1, new_lb - 1)
                lb = new_lb
        accept.__name__ = str(
            'try_shrink(%d, %d)' % (lo, hi)
        )
        return accept

    def simplify_to_lower_bound(self, random, template):
        yield self.lower_bound

    def simplifiers(self, random, template):
        if template == self.lower_bound:
            return
        yield self.simplify_to_lower_bound
        i = 1
        lb = self.lower_bound
        while i + lb < abs(template):
            yield self.try_shrink(i)
            i *= 2

    def from_basic(self, data):
        data = integer_or_bad(data)
        if data < self.lower_bound:
            raise BadData('Value %d out of range [%d, infinity)' % (
                data, self.lower_bound
            ))
        return data

    def to_basic(self, template):
        return text_type(template)


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


class WideRangeIntStrategy(IntStrategy):
    Parameter = namedtuple(
        'Parameter',
        ('center', 'width'),
    )

    def __repr__(self):
        return 'WideRangeIntStrategy()'

    def produce_parameter(self, random):
        return self.Parameter(
            center=random.randint(-2 ** 129, 2 ** 129),
            width=2 ** random.randint(0, 256),
        )

    def produce_template(self, context, parameter):
        return parameter.center + context.random.randint(
            -parameter.width, parameter.width
        )


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
        if self.size_lower_bound >= EFFECTIVELY_INFINITE:
            self.size_lower_bound = float('inf')
        self.size_upper_bound = self.size_lower_bound

    def __repr__(self):
        return 'BoundedIntStrategy(%d, %d)' % (self.start, self.end)

    def strictly_simpler(self, x, y):
        return x < y

    def produce_parameter(self, random):
        n = 1 + dist.geometric(random, 0.01)
        results = []
        for _ in hrange(n):
            results.append(random.randint(self.start, self.end))
        return results

    def from_basic(self, data):
        data = integer_or_bad(data)
        if data < self.start or data > self.end:
            raise BadData('Value %d out of range [%d, %d]' % (
                data, self.start, self.end
            ))
        return data

    def to_basic(self, template):
        return text_type(template)

    def reify(self, value):
        return value

    def produce_template(self, context, parameter):
        if self.start == self.end:
            return self.start
        return context.random.choice(parameter)

    def basic_simplify(self, random, x):
        if x == self.start:
            return

        probe = self.start
        while True:
            yield probe
            new_probe = (x + probe) // 2
            if new_probe > probe:
                probe = new_probe
            else:
                break

        for _ in hrange(10):
            yield random.randint(self.start, x - 1)


def is_integral(value):
    try:
        return int(value) == value
    except (OverflowError, ValueError):
        return False


class FloatStrategy(SearchStrategy):

    """Generic superclass for strategies which produce floats."""

    def __init__(self):
        SearchStrategy.__init__(self)
        self.int_strategy = RandomGeometricIntStrategy()

    def __repr__(self):
        return '%s()' % (self.__class__.__name__,)

    def strictly_simpler(self, x, y):
        if is_integral(x):
            if not is_integral(y):
                return True
            return self.int_strategy.strictly_simpler(int(x), int(y))
        if is_integral(y):
            return False
        if math.isnan(x):
            return False
        if math.isnan(y):
            return True
        if math.isinf(x) and not math.isinf(y):
            return False
        if y > 0:
            return 0 <= x < y
        else:
            # The y == 0 case is handled by is_integral(y)
            assert y < 0
            return x > y

    def to_basic(self, value):
        check_type(float, value)
        return (
            struct.unpack(b'!Q', struct.pack(b'!d', value))[0]
        )

    def from_basic(self, value):
        check_data_type(integer_types, value)
        try:
            return (
                struct.unpack(b'!d', struct.pack(b'!Q', value))[0]
            )
        except (struct.error, ValueError, OverflowError) as e:
            raise BadData(e.args[0])

    def reify(self, value):
        return value

    def simplifiers(self, random, x):
        if x == 0.0:
            return
        yield self.simplify_weird_values
        yield self.push_towards_one
        yield self.simplify_integral
        yield self.basic_simplify

    def simplify_weird_values(self, random, x):
        if math.isnan(x):
            yield 0.0
            yield float('inf')
            yield -float('inf')
            return
        if math.isinf(x):
            yield math.copysign(
                sys.float_info.max, x
            )
            if x < 0:
                yield -x
            return

    def push_towards_one(self, random, x):
        if x > 1.0 and not math.isinf(x):
            assert self.strictly_simpler(1.0, x)
            yield 1.0
            y = math.sqrt(x)
            if is_integral(x):
                y = float(math.floor(y))
            assert(self.strictly_simpler(y, x))
            yield y

    def simplify_integral(self, random, x):
        if not is_integral(x):
            try:
                yield float(math.floor(x))
            except (OverflowError, ValueError):
                pass
            return
        for m in self.int_strategy.full_simplify(random, int(x)):
            yield float(m)

    def basic_simplify(self, random, x):
        if x == 0.0:
            return

        yield 0.0

        if x < 0:
            yield -x
            for t in self.basic_simplify(random, -x):
                yield -t
            return

        if not is_integral(x):
            for e in range(10):
                scale = 2 ** e
                try:
                    y = float(math.floor(x * scale)) / scale
                except (OverflowError, ValueError):
                    break
                yield y


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

    def __init__(self):
        super(JustIntFloats, self).__init__()
        self.int_strategy = RandomGeometricIntStrategy()

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
        FloatStrategy.__init__(self)
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

    def strictly_simpler(self, x, y):
        return x < y

    def simplifiers(self, random, template):
        yield self.basic_simplify

    def basic_simplify(self, random, value):
        if value == self.lower_bound:
            return
        lb = self.lower_bound
        for _ in hrange(32):
            yield lb
            lb = (lb + value) * 0.5

    def from_basic(self, data):
        result = super(FixedBoundedFloatStrategy, self).from_basic(data)
        if result < self.lower_bound or result > self.upper_bound:
            raise BadData('Value %f out of range [%f, %f]' % (
                result, self.lower_bound, self.upper_bound
            ))
        return result


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
        size = 1000.0
        return (
            random.normalvariate(0, size),
            random.expovariate(1.0 / size)
        )

    def produce_template(self, context, param):
        mean, sd = param
        return context.random.normalvariate(mean, sd)


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


class NastyFloats(SampledFromStrategy):

    def __init__(self):
        SampledFromStrategy.__init__(
            self,
            elements=[
                0.0,
                sys.float_info.min,
                -sys.float_info.min,
                -sys.float_info.max,
                sys.float_info.max,
                float('inf'),
                -float('inf'),
                float('nan'),
            ]
        )


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
    if specifier.start == specifier.end:
        return strategy(specifiers.just(specifier.start), settings)

    if math.isinf(specifier.end - specifier.start):
        assert specifier.start < 0 and specifier.end > 0
        return strategy(
            specifiers.FloatRange(0, specifier.end), settings
        ) | strategy(
            specifiers.FloatRange(specifier.start, 0), settings
        )

    return FixedBoundedFloatStrategy(specifier.start, specifier.end)


@strategy.extend_static(int)
def int_strategy(specifier, settings):
    return (
        RandomGeometricIntStrategy() |
        WideRangeIntStrategy()
    )


@strategy.extend(specifiers.IntegersFrom)
def integers_from_strategy(specifier, settings):
    return IntegersFromStrategy(specifier.lower_bound)


@strategy.extend_static(float)
def define_float_strategy(specifier, settings):
    return WrapperFloatStrategy(
        GaussianFloatStrategy() |
        BoundedFloatStrategy() |
        ExponentialFloatStrategy() |
        JustIntFloats() |
        NastyFloats() |
        FullRangeFloats()
    )


@strategy.extend_static(complex)
def define_complex_strategy(specifier, settings):
    return ComplexStrategy(strategy((float, float), settings))


@strategy.extend_static(Decimal)
def define_decimal_strategy(specifier, settings):
    return (
        strategy(float, settings).map(specifier) |
        strategy(Fraction, settings).map(
            lambda f: specifier(f.numerator) / f.denominator
        )
    )


@strategy.extend_static(Fraction)
def define_fraction_strategy(specifier, settings):
    return strategy((int, specifiers.integers_from(1))).map(
        lambda t: Fraction(*t)
    )
