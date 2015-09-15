# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import sys
import math
import struct
from collections import namedtuple

import hypothesis.internal.distributions as dist
from hypothesis.utils.size import clamp
from hypothesis.internal.compat import hrange, text_type, integer_types
from hypothesis.searchstrategy.misc import SampledFromStrategy
from hypothesis.searchstrategy.strategies import BadData, check_type, \
    infinitish, SearchStrategy, check_data_type, MappedSearchStrategy


def integer_or_bad(data):
    check_data_type(text_type, data)
    try:
        return int(data)
    except ValueError:
        raise BadData(u'Invalid integer %r' % (data,))


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
            u'try_shrink(%d, %d)' % (lo, hi)
        )
        return accept


class IntegersFromStrategy(SearchStrategy):

    def __init__(self, lower_bound, average_size=1000.0):
        super(IntegersFromStrategy, self).__init__()
        self.lower_bound = lower_bound
        self.average_size = average_size

    def __repr__(self):
        return u'IntegersFromStrategy(%d)' % (self.lower_bound,)

    def draw_parameter(self, random):
        return clamp(
            0.0,
            random.random() * 2 / self.average_size,
            1 - 10e-6,
        )

    def draw_template(self, random, parameter):
        return dist.geometric(random, parameter)

    def reify(self, template):
        return self.lower_bound + template

    def try_shrink(self, i):
        lo = i
        hi = 2 * i

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
            u'try_shrink(%d, %d)' % (lo, hi)
        )
        return accept

    def simplify_to_lower_bound(self, random, template):
        yield 0

    def simplifiers(self, random, template):
        if template == 0:
            return
        yield self.simplify_to_lower_bound
        i = 1
        while i < abs(template):
            yield self.try_shrink(i)
            i *= 2

    def from_basic(self, data):
        data = integer_or_bad(data)
        if data < 0:
            raise BadData(u'Value %d out of range [0, infinity)' % (
                data,
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
        u'Parameter',
        (u'negative_probability', u'p')
    )

    def __repr__(self):
        return u'RandomGeometricIntStrategy()'

    def draw_parameter(self, random):
        return self.Parameter(
            negative_probability=random.betavariate(0.5, 0.5),
            p=random.betavariate(0.2, 1.8),
        )

    def draw_template(self, random, parameter):
        value = dist.geometric(random, parameter.p)
        if dist.biased_coin(random, parameter.negative_probability):
            value = -value
        return value


class WideRangeIntStrategy(IntStrategy):
    Parameter = namedtuple(
        u'Parameter',
        (u'center', u'width'),
    )

    def __repr__(self):
        return u'WideRangeIntStrategy()'

    def draw_parameter(self, random):
        return self.Parameter(
            center=random.randint(-2 ** 129, 2 ** 129),
            width=2 ** random.randint(0, 256),
        )

    def draw_template(self, random, parameter):
        return parameter.center + random.randint(
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
            raise ValueError(u'Invalid range [%d, %d]' % (start, end))
        self.template_upper_bound = infinitish(end - start + 1)

    def __repr__(self):
        return u'BoundedIntStrategy(%d, %d)' % (self.start, self.end)

    def strictly_simpler(self, x, y):
        return x < y

    def draw_parameter(self, random):
        n = 1 + dist.geometric(random, 0.01)
        results = []
        for _ in hrange(n):
            results.append(random.randint(self.start, self.end))
        return results

    def from_basic(self, data):
        data = integer_or_bad(data)
        if data < self.start or data > self.end:
            raise BadData(u'Value %d out of range [%d, %d]' % (
                data, self.start, self.end
            ))
        return data

    def to_basic(self, template):
        return text_type(template)

    def reify(self, value):
        return value

    def draw_template(self, random, parameter):
        return random.choice(parameter)

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
        return u'%s()' % (self.__class__.__name__,)

    def strictly_simpler(self, x, y):
        if math.isnan(x):
            return False
        if math.isnan(y):
            return True
        if math.isinf(y) and not math.isinf(x):
            return True
        if math.isinf(x) and not math.isinf(y):
            return False
        if x < 0 and y >= 0:
            return False
        if y < 0 and x >= 0:
            return True
        if is_integral(x):
            if not is_integral(y):
                return True
            return self.int_strategy.strictly_simpler(int(x), int(y))
        if is_integral(y):
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
        except (struct.error, ValueError, OverflowError, TypeError) as e:
            raise BadData(e.args[0])

    def reify(self, value):
        return float(value)

    def simplifiers(self, random, x):
        if x == 0.0:
            return
        yield self.simplify_weird_values
        yield self.push_towards_one
        try:
            for simplify in self.int_strategy.simplifiers(
                random, int(math.floor(x))
            ):
                yield self.simplify_integral(simplify)
        except (OverflowError, ValueError):
            pass
        yield self.basic_simplify

    def simplify_weird_values(self, random, x):
        if math.isnan(x):
            yield 0.0
            yield float(u'inf')
            yield -float(u'inf')
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

    def simplify_integral(self, simplify):
        def accept(random, x):
            if not is_integral(x):
                try:
                    yield float(math.floor(x))
                except (OverflowError, ValueError):
                    pass
                return
            for m in simplify(random, int(math.floor(x))):
                yield float(m)
        accept.__name__ = str(
            u'simplify_integral(%s)' % (simplify.__name__,)
        )
        return accept

    def basic_simplify(self, random, x):
        if x == 0.0:
            return

        yield 0.0

        if x < 0:
            yield -x
            for t in self.basic_simplify(random, -x):
                yield -t
            return
        if x < 1:
            return

        if not is_integral(x):
            for e in range(10):
                scale = 2 ** e
                try:
                    y = float(math.floor(x * scale)) / scale
                except (OverflowError, ValueError):
                    break
                yield y

STANDARD_NAN = float(u'nan')


class WrapperFloatStrategy(FloatStrategy):

    def __init__(self, sub_strategy):
        super(WrapperFloatStrategy, self).__init__()
        self.sub_strategy = sub_strategy

    def __repr__(self):
        return u'WrapperFloatStrategy(%r)' % (self.sub_strategy,)

    def draw_parameter(self, random):
        return self.sub_strategy.draw_parameter(random)

    def draw_template(self, random, pv):
        template = self.sub_strategy.reify(
            self.sub_strategy.draw_template(random, pv))
        if math.isnan(template):
            return STANDARD_NAN
        else:
            return template


class JustIntFloats(FloatStrategy):

    def __init__(self):
        super(JustIntFloats, self).__init__()
        self.int_strategy = RandomGeometricIntStrategy()

    def draw_parameter(self, random):
        return self.int_strategy.draw_parameter(random)

    def draw_template(self, random, pv):
        return float(self.int_strategy.draw_template(random, pv))


def compose_float(sign, exponent, fraction):
    as_long = (sign << 63) | (exponent << 52) | fraction
    return struct.unpack(b'!d', struct.pack(b'!Q', as_long))[0]


class FullRangeFloats(FloatStrategy):

    Parameter = namedtuple(
        u'Parameter',
        (u'negative_probability', u'subnormal_probability')
    )

    def draw_parameter(self, random):
        return self.Parameter(
            negative_probability=dist.uniform_float(random, 0, 1),
            subnormal_probability=dist.uniform_float(random, 0, 0.5),
        )

    def draw_template(self, random, pv):
        sign = int(dist.biased_coin(random, pv.negative_probability))
        if dist.biased_coin(random, pv.subnormal_probability):
            exponent = 0
        else:
            exponent = random.getrandbits(11)

        return compose_float(
            sign,
            exponent,
            random.getrandbits(52)
        )


class FixedBoundedFloatStrategy(FloatStrategy):

    """A strategy for floats distributed between two endpoints.

    The conditional distribution tries to produce values clustered
    closer to one of the ends.

    """
    Parameter = namedtuple(
        u'Parameter',
        (u'cut', u'leftwards')
    )

    def __init__(self, lower_bound, upper_bound):
        FloatStrategy.__init__(self)
        self.lower_bound = float(lower_bound)
        self.upper_bound = float(upper_bound)
        assert upper_bound >= lower_bound

    def __repr__(self):
        return u'FixedBoundedFloatStrategy(%s, %s)' % (
            self.lower_bound, self.upper_bound,
        )

    def draw_parameter(self, random):
        return self.Parameter(
            cut=random.random(),
            leftwards=dist.biased_coin(random, 0.5)
        )

    def draw_template(self, random, pv):
        random = random
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
        if math.isnan(result):
            raise BadData(u'NaN not allowed in range')
        if result < self.lower_bound or result > self.upper_bound:
            raise BadData(u'Value %f out of range [%f, %f]' % (
                result, self.lower_bound, self.upper_bound
            ))
        return result


class BoundedFloatStrategy(FloatStrategy):

    """A float strategy such that every conditional distribution is bounded but
    the endpoints may be arbitrary."""

    Parameter = namedtuple(
        u'Parameter',
        (u'left', u'length', u'spread'),
    )

    def __init__(self):
        super(BoundedFloatStrategy, self).__init__()
        self.inner_strategy = FixedBoundedFloatStrategy(0, 1)

    def draw_parameter(self, random):
        return self.Parameter(
            left=random.normalvariate(0, 1),
            length=random.expovariate(1),
            spread=self.inner_strategy.draw_parameter(random),
        )

    def draw_template(self, random, pv):
        return pv.left + self.inner_strategy.draw_template(
            random, pv.spread
        ) * pv.length


class GaussianFloatStrategy(FloatStrategy):

    """A float strategy such that every conditional distribution is drawn from
    a gaussian."""

    def draw_parameter(self, random):
        size = 1000.0
        return (
            random.normalvariate(0, size),
            random.expovariate(1.0 / size)
        )

    def draw_template(self, random, param):
        mean, sd = param
        return random.normalvariate(mean, sd)


class ExponentialFloatStrategy(FloatStrategy):

    """
    A float strategy such that every conditional distribution is of the form
    aX + b where a = +/- 1 and X is an exponentially distributed random
    variable.
    """

    Parameter = namedtuple(
        u'Parameter',
        (u'lambd', u'zero_point', u'negative'),
    )

    def draw_parameter(self, random):
        return self.Parameter(
            lambd=random.gammavariate(2, 50),
            zero_point=random.normalvariate(0, 1),
            negative=dist.biased_coin(random, 0.5),
        )

    def draw_template(self, random, pv):
        value = random.expovariate(pv.lambd)
        if pv.negative:
            value = -value
        return pv.zero_point + value


class NastyFloats(SampledFromStrategy):

    def __init__(self):
        SampledFromStrategy.__init__(
            self,
            elements=[
                0.0,
                -0.0,
                sys.float_info.min,
                -sys.float_info.min,
                -sys.float_info.max,
                sys.float_info.max,
                float(u'inf'),
                -float(u'inf'),
                float(u'nan'),
            ]
        )


class ComplexStrategy(MappedSearchStrategy):

    """A strategy over complex numbers, with real and imaginary values
    distributed according to some provided strategy for floating point
    numbers."""

    def __repr__(self):
        return u'ComplexStrategy()'

    def pack(self, value):
        return complex(*value)
