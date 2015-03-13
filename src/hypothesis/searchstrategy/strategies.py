# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from collections import namedtuple

import hypothesis.internal.distributions as dist
from hypothesis.settings import Settings
from hypothesis.extmethod import ExtMethod
from hypothesis.descriptors import OneOf, one_of
from hypothesis.internal.compat import integer_types
from hypothesis.internal.fixers import IdKey, nice_string
from hypothesis.internal.tracker import Tracker


class BuildContext(object):

    def __init__(self, random):
        self.random = random
        self.data = {}

    def examples_for(self, strategy):
        key = IdKey(strategy)
        return self.data.setdefault(key, [])

    def add_example(self, strategy, example):
        self.examples_for(strategy).append(example)


class StrategyExtMethod(ExtMethod):

    def __call__(self, specifier, settings=None):
        if settings is None:
            settings = Settings()
        result = super(StrategyExtMethod, self).__call__(specifier, settings)
        assert isinstance(result, SearchStrategy)
        return result


strategy = StrategyExtMethod()


Infinity = float('inf')


class WrongFormat(ValueError):

    """An exception indicating you have attempted to serialize a value that
    does not match the type described by this format."""


class BadData(ValueError):

    """The data that we got out of the database does not seem to match the data
    we could have put into the database given this schema."""


def check_type(typ, value, e=WrongFormat):
    if not isinstance(value, typ):
        if isinstance(typ, tuple):
            name = 'any of ' + ', '.join(t.__name__ for t in typ)
        else:
            name = typ.__name__
        raise e('Value %r is not an instance of %s' % (
            value, name
        ))


def check_data_type(typ, value):
    check_type(typ, value, BadData)


def check_length(l, value, e=BadData):
    try:
        actual = len(value)
    except TypeError:
        raise e('Excepted type with length but got %r' % (value,))
    if actual != l:
        raise e('Expected %d elements but got %d from %r' % (
            l, actual, value
        ))


def one_of_strategies(xs):
    """Helper function for unioning multiple strategies."""
    xs = tuple(xs)
    if not xs:
        raise ValueError('Cannot join an empty list of strategies')
    if len(xs) == 1:
        return xs[0]
    return OneOfStrategy(xs)


@strategy.extend(OneOf)
def strategy_for_one_of(oneof, settings):
    return one_of_strategies([strategy(d, settings) for d in oneof.elements])


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

    # This should be an object that describes the type of data that this
    # SearchStrategy can produce.
    descriptor = None

    size_lower_bound = Infinity
    size_upper_bound = Infinity

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            nice_string(self.descriptor)
        )

    def __init__(self):
        pass

    def draw_and_produce(self, context):
        return self.draw_template(
            context, self.draw_parameter(context.random))

    def draw_parameter(self, random):
        return self.produce_parameter(random)

    def draw_template(self, context, parameter_value):
        template = self.produce_template(context, parameter_value)
        context.add_example(self, template)
        return template

    def produce_parameter(self, random):
        raise NotImplementedError(  # pragma: no cover
            '%s.produce_parameter()' % (self.__class__.__name__))

    def produce_template(self, context, parameter_value):
        """Given a build context and a value drawn from self.parameter, produce
        a value matching this search strategy's descriptor."""
        raise NotImplementedError(  # pragma: no cover
            '%s.produce_template()' % (self.__class__.__name__))

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

    def reify(self, value):
        """Return a version of value such that if it is mutated this will not
        be reflected in value. If value is immutable it is perfectly acceptable
        to just return value itself.

        This version uses deepcopy and you can count on that remaining
        the case but subclasses should feel free to override it if
        providing copy hooks is not suitable for their needs.

        """
        return value

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
        if not f(t):
            raise ValueError(
                '%r does not satisfy predicate %s' % (t, f))
        tracker = Tracker()
        yield t

        while True:
            simpler = self.simplify(t)
            for s in simpler:
                if tracker.track(s) > 1:
                    continue
                if f(s):
                    yield s
                    t = s
                    break
            else:
                break

    def to_basic(self, template):
        """Convert a template value into basic data, raising WrongFormat if
        this is not an appropriate template."""
        raise NotImplementedError(  # pragma: no cover
            '%s.to_basic()' % (self.__class__.__name__))

    def from_basic(self, value):
        """Convert basic data back to a Template, raising BadData if this could
        not have come from a template for this strategy."""
        raise NotImplementedError(  # pragma: no cover
            '%s.from_basic()' % (self.__class__.__name__))

    def __or__(self, other):
        if not isinstance(other, SearchStrategy):
            raise ValueError('Cannot | a SearchStrategy with %r' % (other,))
        return one_of_strategies((self, other))


@strategy.extend(SearchStrategy)
def strategy_strategy(strategy, settings):
    return strategy


class OneOfStrategy(SearchStrategy):

    """Implements a union of strategies. Given a number of strategies this
    generates values which could have come from any of them.

    The conditional distribution draws uniformly at random from some non-empty
    subset of these strategies and then draws from the conditional distribution
    of that strategy.

    """

    Parameter = namedtuple(
        'Parameter', ('enabled_children', 'child_parameters')
    )

    def __init__(self,
                 strategies):
        SearchStrategy.__init__(self)
        strategies = tuple(strategies)
        if len(strategies) <= 1:
            raise ValueError('Need at least 2 strategies to choose amongst')
        descriptor = one_of([s.descriptor for s in strategies])
        self.descriptor = descriptor
        self.element_strategies = list(strategies)
        self.size_lower_bound = 0
        self.size_upper_bound = 0
        for e in self.element_strategies:
            self.size_lower_bound = max(
                self.size_lower_bound, e.size_lower_bound)
            self.size_upper_bound += e.size_upper_bound

    def reify(self, value):
        s, x = value
        return self.element_strategies[s].reify(x)

    def decompose(self, value):
        s, x = value
        yield self.element_strategies[s].descriptor, x
        for t in self.element_strategies[s].decompose(x):
            yield t

    def produce_parameter(self, random):
        indices = list(range(len(self.element_strategies)))
        enabled = dist.non_empty_subset(
            random,
            indices,
        )
        return self.Parameter(
            enabled_children=enabled,
            child_parameters=[
                self.element_strategies[i].draw_parameter(random)
                if i in enabled else None
                for i in indices
            ]
        )

    def produce_template(self, context, pv):
        assert isinstance(pv, self.Parameter), repr(pv)
        child = context.random.choice(pv.enabled_children)

        return (
            child,
            self.element_strategies[child].draw_template(
                context, pv.child_parameters[child]))

    def simplify(self, x):
        s, value = x
        for y in self.element_strategies[s].simplify(value):
            yield (s, y)

    def to_basic(self, template):
        i, value = template
        return [i, self.element_strategies[i].to_basic(value)]

    def from_basic(self, data):
        check_data_type(list, data)
        check_length(2, data)
        i, value = data
        check_data_type(integer_types, i)
        if i < 0:
            raise BadData('Index out of range: %d < 0' % (i,))
        elif i >= len(self.element_strategies):
            raise BadData(
                'Index out of range: %d >= %d' % (
                    i, len(self.element_strategies)))

        return (i, self.element_strategies[i].from_basic(value))


class MappedSearchStrategy(SearchStrategy):

    """A strategy which is defined purely by conversion to and from another
    strategy.

    Its parameter and distribution come from that other strategy.

    """

    def __init__(self, descriptor, strategy):
        SearchStrategy.__init__(self)
        self.mapped_strategy = strategy
        self.descriptor = descriptor
        self.size_lower_bound = self.mapped_strategy.size_lower_bound
        self.size_upper_bound = self.mapped_strategy.size_upper_bound

    def produce_parameter(self, random):
        return self.mapped_strategy.produce_parameter(random)

    def produce_template(self, context, pv):
        return self.mapped_strategy.produce_template(context, pv)

    def pack(self, x):
        """Take a value produced by the underlying mapped_strategy and turn it
        into a value suitable for outputting from this strategy."""
        raise NotImplementedError(
            '%s.pack()' % (self.__class__.__name__))

    def decompose(self, value):
        return self.mapped_strategy.decompose(value)

    def reify(self, value):
        return self.pack(self.mapped_strategy.reify(value))

    def simplify(self, value):
        for y in self.mapped_strategy.simplify(value):
            yield y

    def to_basic(self, template):
        return self.mapped_strategy.to_basic(template)

    def from_basic(self, data):
        return self.mapped_strategy.from_basic(data)
