# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""Module defining SearchStrategy, which is the core type that Hypothesis uses
to explore data."""

from __future__ import division, print_function, unicode_literals

import sys
import math
import string
import struct
import inspect
import unicodedata
from abc import abstractmethod
from copy import deepcopy
from random import Random

import hypothesis.params as params
import hypothesis.descriptors as descriptors
import hypothesis.internal.utils.distributions as dist
from hypothesis.types import RandomWithSeed
from hypothesis.internal.compat import hrange, hunichr, text_type, \
    binary_type, integer_types
from hypothesis.internal.tracker import Tracker
from hypothesis.internal.utils.fixers import actually_in, nice_string, \
    actually_equal
from hypothesis.internal.utils.reflection import unbind_method


class mix_generators(object):

    """a generator which cycles through these generator arguments.

    Will return all the same values as (x for g in generators for x in
    g) but will do so in an order that mixes the different generators
    up.

    """

    def __init__(self, generators):
        self.generators = list(generators)
        self.next_batch = []
        self.solo_generator = None

    def __iter__(self):
        return self

    def next(self):  # pragma: no cover
        return self.__next__()

    def __next__(self):
        if self.solo_generator is None and len(
            self.generators + self.next_batch
        ) == 1:
            self.solo_generator = (self.generators + self.next_batch)[0]

        if self.solo_generator is not None:
            return next(self.solo_generator)

        while self.generators or self.next_batch:
            if not self.generators:
                self.generators = self.next_batch
                self.generators.reverse()
                self.next_batch = []
            g = self.generators.pop()
            try:
                result = next(g)
                self.next_batch.append(g)
                return result
            except StopIteration:
                pass
        raise StopIteration()


Infinity = float('inf')


class SearchStrategy(object):

    """A SearchStrategy is an object that knows how to explore data of a given
    type.

    A search strategy's data production is defined by two distributions: The
    distribution if its parameter and the conditional distribution given a
    specific parameter value. In general the exact shapes of these should not
    be considered part of a class's contract and may change if a better choice
    is found. Generally the shape of the parameter is highly likely to change
    and the shape of the conditional distribution is quite likely to stay the
    same.

    """

    # A subclass should override this if its data is mutable and must be
    # copied before it is safe to pass to unknown functions.
    has_immutable_data = True

    # This should be an object that describes the type of data that this
    # SearchStrategy can produce.
    descriptor = None

    # This should be an object of type Parameter, values from which will be
    # passed to produce to control the shape of the distribution.
    parameter = None

    size_lower_bound = Infinity
    size_upper_bound = Infinity

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            nice_string(self.descriptor)
        )

    def __init__(self):
        pass

    def has_custom_copy(self):
        try:
            return self.__has_custom_copy
        except AttributeError:
            pass
        self.__has_custom_copy = self.check_has_custom_copy()
        return self.__has_custom_copy

    def check_has_custom_copy(self):
        return (
            unbind_method(self.custom_copy) !=
            unbind_method(SearchStrategy.custom_copy))

    def custom_copy(self, value):
        """Perform a custom copy.

        You don't need to implement this if your type supports deepcopy.

        """
        raise NotImplementedError(
            '%s.custom_copy()' % (self.__class__.__name__))

    def draw_and_produce(self, random):
        return self.produce(random, self.parameter.draw(random))

    @abstractmethod
    def produce(self, random, parameter_value):
        """Given a random number generator and a value drawn from
        self.parameter, produce a value matching this search strategy's
        descriptor."""
        pass  # pragma: no cover

    def decompose(self, value):
        """Returns something iterable over pairs (descriptor, v) where v is
        some value that could have been produced by an appropriate strategy for
        descriptor.

        The idea is that this is supposed to highlight interesting features
        that were used to build the value passed in. e.g. elements of a
        collection. No specific behaviour is required of these values and you
        can do whatever you want, but this can help guide finding interesting
        examples for other tests so if there's something you can do it's worth
        doing.

        Implementation detail: The current way this is used is that all of
        the values produced here will be saved in the database under the
        storage for the provided descriptor if the main value is.

        """
        return ()

    def copy(self, value):
        """Return a version of value such that if it is mutated this will not
        be reflected in value. If value is immutable it is perfectly acceptable
        to just return value itself.

        This version uses deepcopy and you can count on that remaining
        the case but subclasses should feel free to override it if
        providing copy hooks is not suitable for their needs.

        """
        if self.has_custom_copy():
            return self.custom_copy(value)
        elif self.has_immutable_data:
            return value
        else:
            return deepcopy(value)

    def simplify(self, value):
        """Yield a number of values matching this descriptor that are in some
        sense "simpelr" than value. What simpler means is entirely up to
        subclasses and has no specified meaning. The intended interpretation is
        that if you are given a choice between value and an element of
        simplify(value) as an example you would rather one of the latter.

        While it is perfectly acceptable to have cycles in simplify where
        x{i+1} in simplify(xi) and x1 in simplify(x1) implementations should
        try to make a "best effort" attempt not to do this because it will tend
        to cause an unneccessarily large amount of time to be spent in
        simplification as it walks up and down the search space. However it is
        guaranteed to be safe and will not cause infinite loops.

        The results of this function should be a deterministic function of its
        input. If you want randomization, seed it off the value.

        """
        return iter(())

    def could_have_produced(self, x):
        """Is this a value that feasibly could have resulted from produce on
        this strategy.

        It is not strictly required that this method is accurate and the only
        invariant it *must* satisfy is that a value which returns True here
        will never error when passed to simplify, but implementations should
        try to make this as precise as possible as confusing behaviour may
        arise in some cases if it is not, with values produced by one strategy
        being passed to another for simplification when one_of is used.

        """
        d = self.descriptor
        c = d if inspect.isclass(d) else d.__class__
        return isinstance(x, c)

    def simplify_such_that(self, t, f):
        """Perform a greedy search to produce a "simplest" version of t that
        satisfies the predicate s. As each simpler version is found, yield it
        in turn. Stops when it has a value such that no value in simplify on
        the last value found satisfies f.

        Care is taken to avoid cycles in simplify.

        f should produce the same result deterministically. This function may
        raise an error given f such that f(t) returns False sometimes and True
        some other times.

        """
        assert self.could_have_produced(t)
        if not f(t):
            raise ValueError(
                '%r does not satisfy predicate %s' % (t, f))
        tracker = Tracker()
        yield t

        while True:
            simpler = self.simplify(t)
            for s in simpler:
                assert self.could_have_produced(s)
                if tracker.track(s) > 1:
                    continue
                if f(s):
                    yield s
                    t = s
                    break
            else:
                break

    def __or__(self, other):
        if not isinstance(other, SearchStrategy):
            raise ValueError('Cannot | a SearchStrategy with %r' % (other,))
        return one_of_strategies((self, other))


class IntStrategy(SearchStrategy):

    """A generic strategy for integer types that provides the basic methods
    other than produce.

    Subclasses should provide the produce method.

    """
    descriptor = int

    def could_have_produced(self, x):
        return isinstance(x, integer_types)

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
    parameter = params.CompositeParameter(
        negative_probability=params.BetaFloatParameter(0.5, 0.5),
        p=params.BetaFloatParameter(alpha=0.2, beta=1.8),
    )

    def produce(self, random, parameter):
        value = dist.geometric(random, parameter.p)
        if dist.biased_coin(random, parameter.negative_probability):
            value = -value
        return value


class BoundedIntStrategy(SearchStrategy):

    """A strategy for providing integers in some interval with inclusive
    endpoints."""

    descriptor = int
    parameter = params.CompositeParameter()

    def __init__(self, start, end):
        SearchStrategy.__init__(self)
        self.start = start
        self.end = end
        if start > end:
            raise ValueError('Invalid range [%d, %d]' % (start, end))
        self.parameter = params.NonEmptySubset(
            tuple(range(start, end + 1)),
            activation_chance=min(0.5, 3.0 / (end - start + 1))
        )
        self.size_lower_bound = end - start + 1
        self.size_upper_bound = end - start + 1

    def produce(self, random, parameter):
        if self.start == self.end:
            return self.start
        return random.choice(parameter)

    def simplify(self, x):
        if x == self.start:
            return
        for t in hrange(x - 1, self.start - 1, -1):
            yield t
        mid = (self.start + self.end) // 2
        if x > mid:
            yield self.start + (self.end - x)
            for t in hrange(x + 1, self.end + 1):
                yield t

    def could_have_produced(self, i):
        return isinstance(i, integer_types) and (
            self.start <= i <= self.end
        )


class FloatStrategy(SearchStrategy):

    """Generic superclass for strategies which produce floats."""
    descriptor = float

    def __init__(self):
        SearchStrategy.__init__(self)
        self.int_strategy = RandomGeometricIntStrategy()

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

    def could_have_produced(self, value):
        return isinstance(value, float) and not (
            math.isnan(value) or math.isinf(value)
        )


class JustIntFloats(FloatStrategy):

    def __init__(self, int_strategy):
        super(JustIntFloats, self).__init__()
        self.int_strategy = int_strategy
        self.parameter = self.int_strategy.parameter

    def produce(self, random, pv):
        return float(self.int_strategy.produce(random, pv))


def compose_float(sign, exponent, fraction):
    as_long = (sign << 63) | (exponent << 52) | fraction
    return struct.unpack(b'!d', struct.pack(b'!Q', as_long))[0]


class FullRangeFloats(FloatStrategy):
    parameter = params.CompositeParameter(
        negative_probability=params.UniformFloatParameter(0, 1),
        subnormal_probability=params.UniformFloatParameter(0, 0.5),
    )

    def produce(self, random, pv):
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

    def could_have_produced(self, value):
        return isinstance(value, float)


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
    parameter = params.CompositeParameter(
        negative_probability=params.UniformFloatParameter(0, 1),
        min_exponent=params.UniformIntParameter(0, max_exponent)
    )

    def produce(self, random, pv):
        base = math.ldexp(
            random.random(),
            -random.randint(pv.min_exponent, self.max_exponent)
        )
        if dist.biased_coin(random, pv.negative_probability):
            base = -base
        return base


class FixedBoundedFloatStrategy(SearchStrategy):

    """A strategy for floats distributed between two endpoints.

    The conditional distribution tries to produce values clustered
    closer to one of the ends.

    """
    descriptor = float

    parameter = params.CompositeParameter(
        cut=params.UniformFloatParameter(0, 1),
        leftwards=params.BiasedCoin(0.5),
    )

    def __init__(self, lower_bound, upper_bound):
        SearchStrategy.__init__(self)
        self.lower_bound = float(lower_bound)
        self.upper_bound = float(upper_bound)

    def produce(self, random, pv):
        if pv.leftwards:
            left = self.lower_bound
            right = pv.cut
        else:
            left = pv.cut
            right = self.upper_bound
        return left + random.random() * (right - left)

    def simplify(self, value):
        yield self.lower_bound
        yield self.upper_bound
        yield (self.lower_bound + self.upper_bound) * 0.5


class BoundedFloatStrategy(FloatStrategy):

    """A float strategy such that every conditional distribution is bounded but
    the endpoints may be arbitrary."""

    def __init__(self):
        super(BoundedFloatStrategy, self).__init__()
        self.inner_strategy = FixedBoundedFloatStrategy(0, 1)
        self.parameter = params.CompositeParameter(
            left=params.NormalParameter(0, 1),
            length=params.ExponentialParameter(1),
            spread=self.inner_strategy.parameter,
        )

    def produce(self, random, pv):
        return pv.left + self.inner_strategy.produce(
            random, pv.spread
        ) * pv.length


class GaussianFloatStrategy(FloatStrategy):

    """A float strategy such that every conditional distribution is drawn from
    a gaussian."""
    parameter = params.CompositeParameter(
        mean=params.NormalParameter(0, 1),
    )

    def produce(self, random, pv):
        return random.normalvariate(pv.mean, 1)


class ExponentialFloatStrategy(FloatStrategy):

    """
    A float strategy such that every conditional distribution is of the form
    aX + b where a = +/- 1 and X is an exponentially distributed random
    variable.
    """
    parameter = params.CompositeParameter(
        lambd=params.GammaParameter(2, 50),
        zero_point=params.NormalParameter(0, 1),
        negative=params.BiasedCoin(0.5),
    )

    def produce(self, random, pv):
        value = random.expovariate(pv.lambd)
        if pv.negative:
            value = -value
        return pv.zero_point + value


class BoolStrategy(SearchStrategy):

    """A strategy that produces Booleans with a Bernoulli conditional
    distribution."""
    descriptor = bool
    size_lower_bound = 2
    size_upper_bound = 2

    parameter = params.UniformFloatParameter(0, 1)

    def produce(self, random, p):
        return dist.biased_coin(random, p)


class TupleStrategy(SearchStrategy):

    """A strategy responsible for fixed length tuples based on heterogenous
    strategies for each of their elements.

    This also handles namedtuples

    """

    def __init__(self,
                 strategies, tuple_type):
        SearchStrategy.__init__(self)
        strategies = tuple(strategies)
        self.tuple_type = tuple_type
        self.descriptor = self.newtuple([s.descriptor for s in strategies])
        self.element_strategies = strategies
        self.parameter = params.CompositeParameter(
            x.parameter for x in self.element_strategies
        )
        self.has_immutable_data = all(s.has_immutable_data for s in strategies)
        self.size_lower_bound = 1
        self.size_upper_bound = 1
        for e in self.element_strategies:
            self.size_lower_bound *= e.size_lower_bound
            self.size_upper_bound *= e.size_upper_bound

    def could_have_produced(self, xs):
        if xs.__class__ != self.tuple_type:
            return False
        if len(xs) != len(self.element_strategies):
            return False
        return all((s.could_have_produced(x)
                    for s, x in zip(self.element_strategies, xs)))

    def check_has_custom_copy(self):
        return any(e.has_custom_copy() for e in self.element_strategies)

    def custom_copy(self, value):
        return self.newtuple(
            e.copy(v) for e, v in zip(self.element_strategies, value)
        )

    def decompose(self, value):
        assert self.could_have_produced(value)
        return [
            (s.descriptor, v)
            for s, v in zip(self.element_strategies, value)]

    def newtuple(self, xs):
        """Produce a new tuple of the correct type."""
        if self.tuple_type == tuple:
            return tuple(xs)
        else:
            return self.tuple_type(*xs)

    def produce(self, random, pv):
        es = self.element_strategies
        return self.newtuple([
            g.produce(random, v)
            for g, v in zip(es, pv)
        ])

    def simplify(self, x):
        """
        Defined simplification for tuples: We don't change the length of the
        tuple we only try to simplify individual elements of it.
        We first try simplifying each index. We then try pairs of indices.
        After that we stop because it's getting silly.
        """

        generators = []

        def simplify_single(i):
            for s in self.element_strategies[i].simplify(x[i]):
                z = list(x)
                z[i] = s
                yield self.newtuple(z)

        for i in hrange(0, len(x)):
            generators.append(simplify_single(i))

        return mix_generators(generators)


def one_of_strategies(xs):
    """Helper function for unioning multiple strategies."""
    xs = tuple(xs)
    if not xs:
        raise ValueError('Cannot join an empty list of strategies')
    if len(xs) == 1:
        return xs[0]
    return OneOfStrategy(xs)


def _unique(xs):
    """Helper function for removing duplicates from a list whilst preserving
    its order."""
    result = []
    for x in xs:
        if not actually_in(x, result):
            result.append(x)
    return result


class ListStrategy(SearchStrategy):

    """A strategy for lists which takes an intended average length and a
    strategy for each of its element types and generates lists containing any
    of those element types.

    The conditional distribution of the length is geometric, and the
    conditional distribution of each parameter is whatever their
    strategies define.

    """
    has_immutable_data = False

    def __init__(self,
                 strategies, average_length=50.0):
        SearchStrategy.__init__(self)

        self.descriptor = _unique(x.descriptor for x in strategies)
        self.descriptor.sort(key=repr)
        self.element_strategy = one_of_strategies(strategies)
        self.parameter = params.CompositeParameter(
            average_length=params.ExponentialParameter(1.0 / average_length),
            child_parameter=self.element_strategy.parameter,
        )

    def decompose(self, value):
        assert self.could_have_produced(value)
        return [
            (self.element_strategy.descriptor, v)
            for v in value
        ]

    def check_has_custom_copy(self):
        return self.element_strategy.has_custom_copy()

    def custom_copy(self, value):
        return list(map(self.element_strategy.copy, value))

    def produce(self, random, pv):
        length = dist.geometric(random, 1.0 / (1 + pv.average_length))
        result = []
        for _ in hrange(length):
            result.append(
                self.element_strategy.produce(random, pv.child_parameter))
        return result

    def simplify(self, x):
        assert isinstance(x, list)
        if not x:
            return

        yield []

        for i in hrange(0, len(x)):
            if len(x) > 1:
                y = list(x)
                del y[i]
                yield y
            for s in self.element_strategy.simplify(x[i]):
                z = list(x)
                z[i] = s
                yield z

        for i in hrange(0, len(x) - 1):
            z = list(x)
            del z[i]
            del z[i]
            yield z

    def could_have_produced(self, value):
        return isinstance(value, list) and all(
            self.element_strategy.could_have_produced(x)
            for x in value
        )


class MappedSearchStrategy(SearchStrategy):

    """A strategy which is defined purely by conversion to and from another
    strategy.

    Its parameter and distribution come from that other strategy.

    """

    def __init__(self, descriptor, strategy):
        SearchStrategy.__init__(self)
        self.mapped_strategy = strategy
        self.descriptor = descriptor
        self.parameter = self.mapped_strategy.parameter

    def check_has_custom_copy(self):
        return self.mapped_strategy.has_custom_copy()

    @abstractmethod
    def pack(self, x):
        """Take a value produced by the underlying mapped_strategy and turn it
        into a value suitable for outputting from this strategy."""
        pass  # pragma: no cover

    @abstractmethod
    def unpack(self, x):
        """Take a value produced from pack and convert it back to a value that
        could have been produced by the underlying strategy."""
        pass  # pragma: no cover

    def decompose(self, value):
        return self.mapped_strategy.decompose(self.unpack(value))

    def produce(self, random, pv):
        return self.pack(self.mapped_strategy.produce(random, pv))

    def could_have_produced(self, value):
        return super(MappedSearchStrategy, self).could_have_produced(
            value
        ) and self.mapped_strategy.could_have_produced(
            self.unpack(value)
        )

    def simplify(self, x):
        unpacked = self.unpack(x)
        for y in self.mapped_strategy.simplify(unpacked):
            yield self.pack(y)


class ComplexStrategy(SearchStrategy):

    """A strategy over complex numbers, with real and imaginary values
    distributed according to some provided strategy for floating point
    numbers."""
    descriptor = complex

    def __init__(self, float_strategy):
        super(ComplexStrategy, self).__init__()
        self.parameter = params.CompositeParameter(
            real=float_strategy.parameter,
            imaginary=float_strategy.parameter,
        )
        self.float_strategy = float_strategy

    def produce(self, random, pv):
        return complex(
            self.float_strategy.produce(random, pv.real),
            self.float_strategy.produce(random, pv.imaginary),
        )

    def simplify(self, x):
        for t in self.float_strategy.simplify(x.real):
            yield complex(t, x.imag)
        for t in self.float_strategy.simplify(x.imag):
            yield complex(x.real, t)


class SetStrategy(MappedSearchStrategy):

    """A strategy for sets of values, defined in terms of a strategy for lists
    of values."""
    has_immutable_data = False

    def __init__(self, list_strategy):
        super(SetStrategy, self).__init__(
            strategy=list_strategy,
            descriptor=set(list_strategy.descriptor)
        )
        self.size_lower_bound = (
            2 ** list_strategy.element_strategy.size_lower_bound)
        self.size_upper_bound = (
            2 ** list_strategy.element_strategy.size_upper_bound)

    def pack(self, x):
        return set(x)

    def unpack(self, x):
        return list(x)


class FrozenSetStrategy(MappedSearchStrategy):

    """A strategy for frozensets of values, defined in terms of a strategy for
    lists of values."""

    def __init__(self, list_strategy):
        super(FrozenSetStrategy, self).__init__(
            strategy=list_strategy,
            descriptor=frozenset(list_strategy.descriptor)
        )
        self.has_immutable_data = (
            list_strategy.element_strategy.has_immutable_data
        )
        self.size_lower_bound = (
            2 ** list_strategy.element_strategy.size_lower_bound)
        self.size_upper_bound = (
            2 ** list_strategy.element_strategy.size_upper_bound)

    def pack(self, x):
        return frozenset(x)

    def unpack(self, x):
        return list(x)


class OneCharStringStrategy(SearchStrategy):

    """A strategy which generates single character strings of text type."""
    descriptor = text_type
    ascii_characters = (
        text_type('0123456789') + text_type(string.ascii_letters) +
        text_type(' \t\n')
    )
    parameter = params.CompositeParameter(
        ascii_chance=params.UniformFloatParameter(0, 1)
    )

    def produce(self, random, pv):
        if dist.biased_coin(random, pv.ascii_chance):
            return random.choice(self.ascii_characters)
        else:
            while True:
                result = hunichr(random.randint(0, sys.maxunicode))
                if unicodedata.category(result) != 'Cs':
                    return result

    def simplify(self, x):
        if x in self.ascii_characters:
            for i in hrange(self.ascii_characters.index(x) - 1, -1, -1):
                yield self.ascii_characters[i]
        else:
            o = ord(x)
            for c in reversed(self.ascii_characters):
                yield text_type(c)
            if o > 0:
                yield hunichr(o // 2)
                yield hunichr(o - 1)


class StringStrategy(MappedSearchStrategy):

    """A strategy for text strings, defined in terms of a strategy for lists of
    single character text strings."""

    def __init__(self, list_of_one_char_strings_strategy):
        super(StringStrategy, self).__init__(
            descriptor=text_type,
            strategy=list_of_one_char_strings_strategy
        )

    def has_custom_copy(self):
        return False

    def pack(self, ls):
        return text_type('').join(ls)

    def unpack(self, s):
        return list(s)

    def decompose(self, value):
        return ()

    def could_have_produced(self, value):
        return isinstance(value, text_type)


class BinaryStringStrategy(MappedSearchStrategy):

    """A strategy for strings of bytes, defined in terms of a strategy for
    lists of bytes."""

    def has_custom_copy(self):
        return False

    def pack(self, x):
        return binary_type(bytearray(x))

    def decompose(self, value):
        return ()

    def unpack(self, x):
        return list(bytearray(x))

    def could_have_produced(self, value):
        return isinstance(value, binary_type)


class FixedKeysDictStrategy(SearchStrategy):

    """A strategy which produces dicts with a fixed set of keys, given a
    strategy for each of their equivalent values.

    e.g. {'foo' : some_int_strategy} would
    generate dicts with the single key 'foo' mapping to some integer.

    """
    has_immutable_data = False

    def __init__(self, strategy_dict):
        SearchStrategy.__init__(self)
        self.strategy_dict = dict(strategy_dict)
        self.parameter = params.DictParameter({
            k: v.parameter
            for k, v
            in self.strategy_dict.items()
        })
        self.descriptor = {}
        for k, v in self.strategy_dict.items():
            self.descriptor[k] = v.descriptor
        self.size_lower_bound = 1
        self.size_upper_bound = 1
        for e in self.strategy_dict.values():
            self.size_lower_bound *= e.size_lower_bound
            self.size_upper_bound *= e.size_upper_bound

    def check_has_custom_copy(self):
        return any(s.has_custom_copy() for s in self.strategy_dict.values())

    def custom_copy(self, value):
        result = {}
        for k, v in self.strategy_dict.items():
            result[k] = v.copy(value[k])
        return result

    def decompose(self, value):
        return [
            (d, value[k])
            for k, d in self.descriptor.items()
        ]

    def produce(self, random, pv):
        result = {}
        for k, g in self.strategy_dict.items():
            result[k] = g.produce(random, pv[k])
        return result

    def simplify(self, x):
        for k, v in x.items():
            for s in self.strategy_dict[k].simplify(v):
                y = dict(x)
                y[k] = s
                yield y

    def could_have_produced(self, value):
        if not isinstance(value, dict):
            return False
        if len(value) != len(self.descriptor):
            return False
        for k, v in self.strategy_dict.items():
            if k not in value:
                return False
            if not v.could_have_produced(value[k]):
                return False
        return True


class OneOfStrategy(SearchStrategy):

    """Implements a union of strategies. Given a number of strategies this
    generates values which could have come from any of them.

    The conditional distribution draws uniformly at random from some non-empty
    subset of these strategies and then draws from the conditional distribution
    of that strategy.

    Note: If two strategies both return could_have_produced(x) as True then
    when simplifying it is arbitrarily chosen which one gets passed x. The
    specific choice is an implementation detail that should not be relied upon.

    """

    def __init__(self,
                 strategies):
        SearchStrategy.__init__(self)
        flattened_strategies = []
        for s in strategies:
            if isinstance(s, OneOfStrategy):
                flattened_strategies += s.element_strategies
            else:
                flattened_strategies.append(s)
        strategies = tuple(flattened_strategies)
        if len(strategies) <= 1:
            raise ValueError('Need at least 2 strategies to choose amongst')
        descs = _unique(s.descriptor for s in strategies)
        descs.sort(key=repr)
        descriptor = descriptors.one_of(descs)
        self.descriptor = descriptor
        self.element_strategies = list(strategies)
        n = len(self.element_strategies)
        self.parameter = params.CompositeParameter(
            enabled_children=params.NonEmptySubset(range(n)),
            child_parameters=params.CompositeParameter(
                e.parameter for e in self.element_strategies
            )
        )
        self.has_immutable_data = all(
            s.has_immutable_data for s in self.element_strategies)
        self.size_lower_bound = 0
        self.size_upper_bound = 0
        for e in self.element_strategies:
            self.size_lower_bound = max(
                self.size_lower_bound, e.size_lower_bound)
            self.size_upper_bound += e.size_upper_bound

    def check_has_custom_copy(self):
        return any(e.has_custom_copy() for e in self.element_strategies)

    def custom_copy(self, value):
        for e in self.element_strategies:
            if e.could_have_produced(value):
                return e.copy(value)
        raise ValueError('%r could not have produced %r' % (
            self, value
        ))

    def decompose(self, value):
        results = [
            (s.descriptor, value)
            for s in self.element_strategies
            if s.could_have_produced(value)
        ]
        assert results
        return results

    def could_have_produced(self, x):
        return any((s.could_have_produced(x) for s in self.element_strategies))

    def produce(self, random, pv):
        if len(pv.enabled_children) == 1:
            child = pv.enabled_children[0]
        else:
            child = pv.enabled_children[
                random.randint(0, len(pv.enabled_children) - 1)]
        return self.element_strategies[child].produce(
            random, pv.child_parameters[child])

    def simplify(self, x):
        t = Tracker()
        for cs in self.element_strategies:
            if cs.could_have_produced(x):
                for y in cs.simplify(x):
                    if t.track(y) == 1:
                        yield y


class JustStrategy(SearchStrategy):

    """
    A strategy which simply returns a single fixed value with probability 1.
    """
    has_immutable_data = False
    size_lower_bound = 1
    size_upper_bound = 1

    def __init__(self, value):
        SearchStrategy.__init__(self)
        self.descriptor = descriptors.Just(value)
        try:
            deepcopy(value)
        except:
            self.has_immutable_data = True

    def check_has_custom_copy(self):
        return self.has_immutable_data

    def custom_copy(self, value):
        return value

    def __repr__(self):
        return 'JustStrategy(value=%r)' % (self.descriptor.value,)

    parameter = params.CompositeParameter()

    def produce(self, random, pv):
        return self.descriptor.value

    def could_have_produced(self, value):
        return actually_equal(self.descriptor.value, value)


class RandomStrategy(SearchStrategy):

    """A strategy which produces Random objects.

    The conditional distribution is simply a RandomWithSeed seeded with
    a 128 bits of data chosen uniformly at random.

    """
    descriptor = Random
    parameter = params.CompositeParameter()
    has_immutable_data = False

    def produce(self, random, pv):
        return RandomWithSeed(random.getrandbits(128))

    def could_have_produced(self, value):
        return isinstance(value, RandomWithSeed)


class SampledFromStrategy(SearchStrategy):

    """A strategy which samples from a set of elements. This is essentially
    equivalent to using a OneOfStrategy over Just strategies but may be more
    efficient and convenient.

    The conditional distribution chooses uniformly at random from some
    non-empty subset of the elements.

    """

    def __init__(self, elements, descriptor=None):
        SearchStrategy.__init__(self)
        self.elements = tuple(_unique(elements))
        if descriptor is None:
            descriptor = descriptors.SampledFrom(self.elements)
        self.descriptor = descriptor
        self.parameter = params.NonEmptySubset(self.elements)
        self.size_lower_bound = len(self.elements)
        self.size_upper_bound = len(self.elements)

    def produce(self, random, pv):
        return random.choice(pv)

    def could_have_produced(self, value):
        return actually_in(value, self.elements)


class NastyFloats(SampledFromStrategy):

    def __init__(self):
        super(NastyFloats, self).__init__(
            descriptor=float,
            elements=[
                0.0,
                sys.float_info.min,
                -sys.float_info.min,
                float('inf'),
                -float('inf'),
                float('nan'),
            ]
        )


class ExampleAugmentedStrategy(SearchStrategy):

    def __init__(self, main_strategy, examples):
        assert examples
        assert all(main_strategy.could_have_produced(e) for e in examples)
        self.examples = tuple(examples)
        self.main_strategy = main_strategy
        self.descriptor = main_strategy.descriptor
        self.parameter = params.CompositeParameter(
            examples=params.NonEmptySubset(examples),
            example_probability=params.UniformFloatParameter(0.0, 0.5),
            main=main_strategy.parameter
        )
        self.has_immutable_data = main_strategy.has_immutable_data
        if hasattr(main_strategy, 'element_strategy'):
            self.element_strategy = main_strategy.element_strategy
        self.size_lower_bound = main_strategy.size_lower_bound
        self.size_upper_bound = main_strategy.size_upper_bound

    def produce(self, random, pv):
        if dist.biased_coin(random, pv.example_probability):
            return random.choice(pv.examples)
        else:
            return self.main_strategy.produce(random, pv.main)

    def decompose(self, value):
        return self.main_strategy.decompose(value)

    def copy(self, value):
        return self.main_strategy.copy(value)

    def simplify(self, value):
        return self.main_strategy.simplify(value)

    def could_have_produced(self, value):
        return self.main_strategy.could_have_produced(value)
