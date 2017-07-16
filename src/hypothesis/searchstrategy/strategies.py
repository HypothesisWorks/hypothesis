# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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
from hypothesis.internal.lazyformat import lazyformat
from hypothesis.internal.reflection import get_pretty_function_description


def one_of_strategies(xs):
    """Helper function for unioning multiple strategies."""
    xs = tuple(xs)
    if not xs:
        raise ValueError('Cannot join an empty list of strategies')
    return OneOfStrategy(xs)


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
    cached_is_empty = None
    validate_called = False

    @property
    def is_empty(self):
        """Returns True if this strategy can never draw a value and will always
        result in the data being marked invalid.

        The fact that this returns False does not guarantee that a valid value
        can be drawn - this is not intended to be perfect, and is primarily
        intended to be an optimisation for some cases.

        """
        if self.cached_is_empty is None:
            # This isn't an error, but instead is to deal with recursive
            # strategy definitions that refer to themselves. This ensures that
            # in a recursive call we will return False. This results in us
            # returning False in some cases where it would be valid to return
            # True, but is_empty only needs to be a conservative approximation
            # anyway, so that's fine.
            self.cached_is_empty = False
            self.cached_is_empty = self.calc_is_empty()
        return self.cached_is_empty

    def calc_is_empty(self):
        return False

    def example(self, random=None):
        """Provide an example of the sort of value that this strategy
        generates. This is biased to be slightly simpler than is typical for
        values from this strategy, for clarity purposes.

        This method shouldn't be taken too seriously. It's here for interactive
        exploration of the API, not for any sort of real testing.

        This method is part of the public API.

        """
        from hypothesis import find, settings, Verbosity
        try:
            return find(
                self,
                lambda x: True,
                random=random,
                settings=settings(
                    max_shrinks=0,
                    max_iterations=1000,
                    database=None,
                    verbosity=Verbosity.quiet,
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

    @property
    def branches(self):
        return [self]

    def __or__(self, other):
        """Return a strategy which produces values by randomly drawing from one
        of this strategy or the other strategy.

        This method is part of the public API.

        """
        if not isinstance(other, SearchStrategy):
            raise ValueError('Cannot | a SearchStrategy with %r' % (other,))
        return one_of_strategies((self, other))

    def validate(self):
        """Throw an exception if the strategy is not valid.

        This can happen due to lazy construction

        """
        if self.validate_called:
            return
        try:
            self.validate_called = True
            self.do_validate()
        except:
            self.validate_called = False
            raise

    def do_validate(self):
        pass

    def do_draw(self, data):
        raise NotImplementedError('%s.do_draw' % (type(self).__name__,))

    def __init__(self):
        pass


class OneOfStrategy(SearchStrategy):

    """Implements a union of strategies. Given a number of strategies this
    generates values which could have come from any of them.

    The conditional distribution draws uniformly at random from some
    non-empty subset of these strategies and then draws from the
    conditional distribution of that strategy.

    """

    def __init__(self, strategies, bias=None):
        SearchStrategy.__init__(self)
        strategies = tuple(strategies)
        self.original_strategies = list(strategies)
        self.__element_strategies = None
        self.bias = bias
        self.__in_branches = False
        if bias is not None:
            assert 0 < bias < 1
            self.sampler = cu.Sampler(
                [bias ** i for i in range(len(strategies))])
        else:
            self.sampler = None

    def calc_is_empty(self):
        return len(self.element_strategies) == 0

    @property
    def element_strategies(self):
        from hypothesis.strategies import check_strategy
        if self.__element_strategies is None:
            strategies = []
            for arg in self.original_strategies:
                check_strategy(arg)
                if not arg.is_empty:
                    strategies.extend(
                        [s for s in arg.branches if not s.is_empty])
            pruned = []
            seen = set()
            for s in strategies:
                if s is self:
                    continue
                if s in seen:
                    continue
                seen.add(s)
                pruned.append(s)
            self.__element_strategies = pruned
        return self.__element_strategies

    def do_draw(self, data):
        n = len(self.element_strategies)
        if n == 0:
            data.mark_invalid()
        elif n == 1:
            return self.element_strategies[0].do_draw(data)
        elif self.sampler is None:
            i = cu.integer_range(data, 0, n - 1)
        else:
            i = self.sampler.sample(data)

        return data.draw(self.element_strategies[i])

    def __repr__(self):
        return ' | '.join(map(repr, self.original_strategies))

    def do_validate(self):
        for e in self.element_strategies:
            e.validate()

    @property
    def branches(self):
        if self.bias is None and not self.__in_branches:
            try:
                self.__in_branches = True
                return self.element_strategies
            finally:
                self.__in_branches = False
        else:
            return [self]


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

    def calc_is_empty(self):
        return self.mapped_strategy.is_empty

    def __repr__(self):
        if not hasattr(self, '_cached_repr'):
            self._cached_repr = '%r.map(%s)' % (
                self.mapped_strategy, get_pretty_function_description(
                    self.pack)
            )
        return self._cached_repr

    def do_validate(self):
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

    @property
    def branches(self):
        return [
            MappedSearchStrategy(pack=self.pack, strategy=strategy)
            for strategy in self.mapped_strategy.branches
        ]


class FilteredStrategy(SearchStrategy):

    def __init__(self, strategy, condition):
        super(FilteredStrategy, self).__init__()
        self.condition = condition
        self.filtered_strategy = strategy

    def calc_is_empty(self):
        return self.filtered_strategy.is_empty

    def __repr__(self):
        if not hasattr(self, '_cached_repr'):
            self._cached_repr = '%r.filter(%s)' % (
                self.filtered_strategy, get_pretty_function_description(
                    self.condition)
            )
        return self._cached_repr

    def do_validate(self):
        self.filtered_strategy.validate()

    def do_draw(self, data):
        for i in hrange(3):
            start_index = data.index
            value = data.draw(self.filtered_strategy)
            if self.condition(value):
                return value
            else:
                if i == 0:
                    data.note_event(lazyformat(
                        'Retried draw from %r to satisfy filter', self,))
                # This is to guard against the case where we consume no data.
                # As long as we consume data, we'll eventually pass or raise.
                # But if we don't this could be an infinite loop.
                assume(data.index > start_index)
        data.note_event('Aborted test because unable to satisfy %r' % (
            self,
        ))
        data.mark_invalid()

    @property
    def branches(self):
        branches = [
            FilteredStrategy(strategy=strategy, condition=self.condition)
            for strategy in self.filtered_strategy.branches
        ]
        return branches
