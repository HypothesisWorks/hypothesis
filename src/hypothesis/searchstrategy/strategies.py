# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from random import Random
from collections import namedtuple

import hypothesis.internal.distributions as dist
from hypothesis.errors import BadData, WrongFormat
from hypothesis.settings import Settings
from hypothesis.specifiers import OneOf
from hypothesis.internal.compat import hrange, integer_types
from hypothesis.utils.extmethod import ExtMethod
from hypothesis.internal.tracker import Tracker


class BuildContext(object):

    def __init__(self, random):
        self.random = random


class StrategyExtMethod(ExtMethod):

    def __call__(self, specifier, settings=None):
        if settings is None:
            settings = Settings()
        result = super(StrategyExtMethod, self).__call__(specifier, settings)
        assert isinstance(result, SearchStrategy)
        return result


strategy = StrategyExtMethod()


Infinity = float('inf')


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

    Except where noted otherwise, methods on this class are not part of the
    public API and their behaviour may change significantly between minor
    version releases. They will generally be stable between patch releases.

    With that in mind, here is how SearchStrategy works.

    A search strategy is responsible for generating, simplifying and
    serializing examples for saving.

    In order to do this a strategy has three types (where type here is more
    precise than just the class of the value. For example a tuple of ints
    should be considered different from a tuple of strings):

    1. The strategy parameter type
    2. The strategy template type
    3. The generated type

    Of these, the first two should be considered to be private implementation
    details of a strategy and the only valid thing to do them is to pass them
    back to the search strategy. Additionally, templates may be compared for
    equality and hashed.

    Templates must be of quite a restricted type. A template may be any of the
    following:

    1. Any instance of the types bool, float, int, str (unicode on 2.7)
    2. None
    3. Any tuple or namedtuple of valid template types
    4. Any frozenset of valid template types

    This may be relaxed a bit in future, but the requirement that templates are
    hashable probably won't be.

    This may all seem overly complicated but it's for a fairly good reason.
    For more discussion of the motivation see
    http://hypothesis.readthedocs.org/en/master/internals.html

    Given these, data generation happens in three phases:

    1. Draw a parameter value from a random number (defined by
       produce_parameter)
    2. Given a parameter value and a build context, draw a random template
    3. Reify a template value, deterministically turning it into a value of
       the desired type.

    Data simplification proceeds on template values, taking a template and
    providing a generator over some examples of similar but simpler templates.

    """

    def example(self):
        """Provide an example of the sort of value that this strategy
        generates. This is biased to be slightly simpler than is typical for
        values from this strategy, for clarity purposes.

        This method shouldn't be taken too seriously. It's here for interactive
        exploration of the API, not for any sort of real testing.

        This method is part of the  public API.

        """
        random = Random()
        context = BuildContext(random)
        template = min((
            self.draw_and_produce(context)
            for _ in hrange(3)
        ), key=self.size)
        return self.reify(template)

    def map(self, pack):
        """Returns a new strategy that generates values by generating a value
        from this strategy and then calling pack() on the result, giving that.

        This method is part of the  public API.

        """
        return MappedSearchStrategy(
            pack=pack, strategy=self
        )

    def __or__(self, other):
        """Return a strategy which produces values by randomly drawing from one
        of this strategy or the other strategy.

        This method is part of the  public API.

        """
        if not isinstance(other, SearchStrategy):
            raise ValueError('Cannot | a SearchStrategy with %r' % (other,))
        return one_of_strategies((self, other))

    # HERE BE DRAGONS. All below is non-public API of varying degrees of
    # stability.

    # Methods to be overridden by subclasses

    def produce_parameter(self, random):
        """Produce a random valid parameter for this strategy, using only data
        from the provided random number generator.

        Note: You should not call this directly. Call draw_parameter instead.

        """
        raise NotImplementedError(  # pragma: no cover
            '%s.produce_parameter()' % (self.__class__.__name__))

    def produce_template(self, context, parameter_value):
        """Given this build context and this parameter value, produce a random
        valid template for this strategy.

        Note: You should not call this directly. Call draw_template instead.

        """
        raise NotImplementedError(  # pragma: no cover
            '%s.produce_template()' % (self.__class__.__name__))

    def reify(self, template):
        """Given a template value, deterministically convert it into a value of
        the desired final type."""
        raise NotImplementedError(  # pragma: no cover
            '%s.reify()' % (self.__class__.__name__))

    def to_basic(self, template):
        """Convert a template value for this strategy into basic data (see
        hypothesis.dabase.formats for the definition of basic data)"""
        raise NotImplementedError(  # pragma: no cover
            '%s.to_basic()' % (self.__class__.__name__))

    def from_basic(self, value):
        """Convert basic data back to a template, raising BadData if the
        provided data cannot be converted into a valid template for this
        strategy."""
        raise NotImplementedError(  # pragma: no cover
            '%s.from_basic()' % (self.__class__.__name__))

    # Gory implementation details

    # Provide bounds on the number of available templates
    # The intended interpretation is that size_lower_bound means "if you've
    # only found this many templates don't worry about it" and size_upper_bound
    # means "if you've found this many templates there definitely aren't any
    # more. Stop"
    # Generally speaking once this reaches numbers >= 1000 or so you might as
    # well just consider it infinite.
    size_lower_bound = Infinity
    size_upper_bound = Infinity

    def __init__(self):
        pass

    def draw_and_produce(self, context):
        return self.draw_template(
            context, self.draw_parameter(context.random))

    def size(self, template):
        """Gives an approximate estimate of how "large" this template value is.

        This doesn't really matter for anything, it's just a convenience
        used to implement example().

        """
        def basic_size(x):
            try:
                if len(x) == 1:
                    return 1
            except TypeError:
                return 1
            return sum(map(basic_size, x))
        return basic_size(self.to_basic(template))

    def draw_parameter(self, random):
        """Draw a new parameter value given this random number generator.

        You should not override this method. Override produce_parameter
        instead. Right now this calls produce_parameter directly, but
        it's a placeholder for when that might not be the case later.

        """
        return self.produce_parameter(random)

    def draw_template(self, context, parameter_value):
        """Draw a new template value given this build context and parameter
        value.

        You should not override this method. Override produce_template
        instead. Right now this calls produce_template directly, but
        it's a placeholder for when that might not be the case later.

        """
        return self.produce_template(context, parameter_value)

    def simplify(self, template):
        """Given a template, return a generator which yields a number of
        templates that are "like this template but simpler". simpler has no
        defined semantic meaning here and can be whatever you feel like.

        General tips for a good simplify:

            1. The generator shouldn't yield too many values. A few hundred is
               fine, but if you're generating millions of simplifications you
               may wish to reconsider your life choices and evaluate which ones
               actually matter to you.
            2. Cycles in simplify are fine, but the simplify graph should be
               bounded in the sense that there should be no infinite acyclic
               paths where a1 simplifies to a2 simplifies to ...
            3. Try major simplifications first to see if you get lucky. Yield
               a minimal element, throw out half of your data, etc. Providing
               shortcuts in the graph will speed up the simplification process
               a lot.

        """
        return iter(())

    def simplify_such_that(self, t, f):
        """Perform a greedy search to produce a "simplest" version of a
        template that satisfies some predicate.

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
        self.element_strategies = list(strategies)
        self.size_lower_bound = 0
        self.size_upper_bound = 0
        for e in self.element_strategies:
            self.size_lower_bound = max(
                self.size_lower_bound, e.size_lower_bound)
            self.size_upper_bound += e.size_upper_bound

    def __repr__(self):
        return ' | '.join(map(repr, self.element_strategies))

    def reify(self, value):
        s, x = value
        return self.element_strategies[s].reify(x)

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

    def __init__(self, strategy, pack=None):
        SearchStrategy.__init__(self)
        self.mapped_strategy = strategy
        self.size_lower_bound = self.mapped_strategy.size_lower_bound
        self.size_upper_bound = self.mapped_strategy.size_upper_bound
        if pack is not None:
            self.pack = pack

    def __repr__(self):
        return 'MappedSearchStrategy(%r, %s)' % (
            self.mapped_strategy, self.pack.__name__
        )

    def produce_parameter(self, random):
        return self.mapped_strategy.produce_parameter(random)

    def produce_template(self, context, pv):
        return self.mapped_strategy.produce_template(context, pv)

    def pack(self, x):
        """Take a value produced by the underlying mapped_strategy and turn it
        into a value suitable for outputting from this strategy."""
        raise NotImplementedError(
            '%s.pack()' % (self.__class__.__name__))

    def reify(self, value):
        return self.pack(self.mapped_strategy.reify(value))

    def simplify(self, value):
        for y in self.mapped_strategy.simplify(value):
            yield y

    def to_basic(self, template):
        return self.mapped_strategy.to_basic(template)

    def from_basic(self, data):
        return self.mapped_strategy.from_basic(data)
