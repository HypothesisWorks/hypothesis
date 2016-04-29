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

import hypothesis.internal.conjecture.utils as cu
from hypothesis.errors import NoExamples, NoSuchExample, Unsatisfiable, \
    UnsatisfiedAssumption
from hypothesis.control import assume, reject
from hypothesis.internal.compat import hrange
from hypothesis.internal.reflection import get_pretty_function_description


def one_of_strategies(xs):
    """Helper function for unioning multiple strategies."""
    xs = tuple(xs)
    if not xs:
        raise ValueError('Cannot join an empty list of strategies')
    from hypothesis.strategies import one_of
    return one_of(xs)


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
       draw_parameter)
    2. Given a parameter value and a Random, draw a random template
    3. Reify a template value, deterministically turning it into a value of
       the desired type.

    Data simplification proceeds on template values, taking a template and
    providing a generator over some examples of similar but simpler templates.

    """

    supports_find = True
    is_empty = False

    def example(self, random=None):
        """Provide an example of the sort of value that this strategy
        generates. This is biased to be slightly simpler than is typical for
        values from this strategy, for clarity purposes.

        This method shouldn't be taken too seriously. It's here for interactive
        exploration of the API, not for any sort of real testing.

        This method is part of the public API.

        """
        from hypothesis import find, settings
        try:
            return find(
                self,
                lambda x: True,
                random=random,
                settings=settings(
                    max_shrinks=0,
                    max_iterations=1000,
                    database=None
                )
            )
        except (NoSuchExample, Unsatisfiable):
            raise NoExamples(
                u'Could not find any valid examples in 100 tries'
            )

    def map(self, pack):
        """Returns a new strategy that generates values by generating a value
        from this strategy and then calling pack() on the result, giving that.

        This method is part of the public API.

        """
        return MappedSearchStrategy(
            pack=pack, strategy=self
        )

    def flatmap(self, expand):
        """Returns a new strategy that generates values by generating a value
        from this strategy, say x, then generating a value from
        strategy(expand(x))

        This method is part of the public API.

        """
        from hypothesis.searchstrategy.flatmapped import FlatMapStrategy
        return FlatMapStrategy(
            expand=expand, strategy=self
        )

    def filter(self, condition):
        """Returns a new strategy that generates values from this strategy
        which satisfy the provided condition. Note that if the condition is too
        hard to satisfy this might result in your tests failing with
        Unsatisfiable.

        This method is part of the public API.

        """
        return FilteredStrategy(
            condition=condition,
            strategy=self,
        )

    def __or__(self, other):
        """Return a strategy which produces values by randomly drawing from one
        of this strategy or the other strategy.

        This method is part of the public API.

        """
        if not isinstance(other, SearchStrategy):
            raise ValueError('Cannot | a SearchStrategy with %r' % (other,))
        if other.is_empty:
            return self
        return one_of_strategies((self, other))

    def validate(self):
        """Through an exception if the strategy is not valid.

        This can happen due to lazy construction

        """
        pass

    def do_draw(self, data):
        raise NotImplementedError('%s.do_draw' % (type(self).__name__,))

    def __init__(self):
        pass


class OneOfStrategy(SearchStrategy):

    """Implements a union of strategies. Given a number of strategies this
    generates values which could have come from any of them.

    The conditional distribution draws uniformly at random from some non-empty
    subset of these strategies and then draws from the conditional distribution
    of that strategy.

    """

    def __init__(self, strategies, bias=None):
        SearchStrategy.__init__(self)
        strategies = tuple(strategies)
        self.element_strategies = list(strategies)
        self.bias = bias
        if bias is not None:
            assert 0 < bias < 1
            self.weights = [bias ** i for i in range(len(strategies))]

    def do_draw(self, data):
        n = len(self.element_strategies)
        if self.bias is None:
            i = cu.integer_range(data, 0, n - 1)
        else:
            def biased_i(random):
                while True:
                    i = random.randint(0, n - 1)
                    if random.random() <= self.weights[i]:
                        return i
            i = cu.integer_range_with_distribution(
                data, 0, n - 1, biased_i)

        return data.draw(self.element_strategies[i])

    def __repr__(self):
        return ' | '.join(map(repr, self.element_strategies))

    def validate(self):
        for e in self.element_strategies:
            e.validate()


class MappedSearchStrategy(SearchStrategy):

    """A strategy which is defined purely by conversion to and from another
    strategy.

    Its parameter and distribution come from that other strategy.

    """

    def __init__(self, strategy, pack=None):
        SearchStrategy.__init__(self)
        self.mapped_strategy = strategy
        if pack is not None:
            self.pack = pack
        self.is_empty = strategy.is_empty

    def __repr__(self):
        if not hasattr(self, '_cached_repr'):
            self._cached_repr = '%r.map(%s)' % (
                self.mapped_strategy, get_pretty_function_description(
                    self.pack)
            )
        return self._cached_repr

    def validate(self):
        self.mapped_strategy.validate()

    def pack(self, x):
        """Take a value produced by the underlying mapped_strategy and turn it
        into a value suitable for outputting from this strategy."""
        raise NotImplementedError(
            '%s.pack()' % (self.__class__.__name__))

    def do_draw(self, data):
        for _ in range(3):
            i = data.index
            try:
                return self.pack(self.mapped_strategy.do_draw(data))
            except UnsatisfiedAssumption:
                if data.index == i:
                    raise
        reject()


class FilteredStrategy(SearchStrategy):

    def __init__(self, strategy, condition):
        super(FilteredStrategy, self).__init__()
        self.condition = condition
        self.filtered_strategy = strategy
        self.is_empty = strategy.is_empty

    def __repr__(self):
        if not hasattr(self, '_cached_repr'):
            self._cached_repr = '%r.filter(%s)' % (
                self.filtered_strategy, get_pretty_function_description(
                    self.condition)
            )
        return self._cached_repr

    def validate(self):
        self.filtered_strategy.validate()

    def do_draw(self, data):
        for _ in hrange(3):
            start_index = data.index
            value = data.draw(self.filtered_strategy)
            if self.condition(value):
                return value
            else:
                # This is to guard against the case where we consume no data.
                # As long as we consume data, we'll eventually pass or raise.
                # But if we don't this could be an infinite loop.
                assume(data.index > start_index)
        data.mark_invalid()
