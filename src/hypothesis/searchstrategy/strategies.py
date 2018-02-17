# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

import hashlib
from collections import defaultdict

import hypothesis.internal.conjecture.utils as cu
from hypothesis.errors import NoExamples, NoSuchExample, Unsatisfiable, \
    UnsatisfiedAssumption
from hypothesis.control import assume, reject, _current_build_context
from hypothesis._settings import note_deprecation
from hypothesis.internal.compat import hrange, qualname, bit_length, \
    str_to_bytes, int_from_bytes
from hypothesis.utils.conventions import UniqueIdentifier
from hypothesis.internal.lazyformat import lazyformat
from hypothesis.internal.reflection import get_pretty_function_description

calculating = UniqueIdentifier('calculating')


LABEL_MASK = 2 ** 64 - 1


def calc_label(cls):
    name = str_to_bytes(qualname(cls))
    hashed = hashlib.md5(name).digest()
    return int_from_bytes(hashed[:8])


def combine_labels(*labels):
    label = 0
    for l in labels:
        label = (label << 1) & LABEL_MASK
        label ^= l
    return label


def one_of_strategies(xs):
    """Helper function for unioning multiple strategies."""
    xs = tuple(xs)
    if not xs:
        raise ValueError('Cannot join an empty list of strategies')
    return OneOfStrategy(xs)


class SearchStrategy(object):
    """A SearchStrategy is an object that knows how to explore data of a given
    type.

    Except where noted otherwise, methods on this class are not part of
    the public API and their behaviour may change significantly between
    minor version releases. They will generally be stable between patch
    releases.

    """

    supports_find = True
    validate_called = False
    __label = None

    def recursive_property(name, default):
        """Handle properties which may be mutually recursive among a set of
        strategies.

        These are essentially lazily cached properties, with the ability to set
        an override: If the property has not been explicitly set, we calculate
        it on first access and memoize the result for later.

        The problem is that for properties that depend on each other, a naive
        calculation strategy may hit infinite recursion. Consider for example
        the property is_empty. A strategy defined as x = st.deferred(lambda x)
        is certainly empty (in order ot draw a value from x we would have to
        draw a value from x, for which we would have to draw a value from x,
        ...), but in order to calculate it the naive approach would end up
        calling x.is_empty in order to calculate x.is_empty in order to etc.

        The solution is one of fixed point calculation. We start with a default
        value that is the value of the property in the absence of evidence to
        the contrary, and then update the values of the property for all
        dependent strategies until we reach a fixed point.

        The approach taken roughly follows that in section 4.2 of Adams,
        Michael D., Celeste Hollenbeck, and Matthew Might. "On the complexity
        and performance of parsing with derivatives." ACM SIGPLAN Notices 51.6
        (2016): 224-236.

        """
        cache_key = 'cached_' + name
        calculation = 'calc_' + name
        force_key = 'force_' + name

        def forced_value(target):
            try:
                return getattr(target, force_key)
            except AttributeError:
                return getattr(target, cache_key)

        def accept(self):
            try:
                return forced_value(self)
            except AttributeError:
                pass

            mapping = {}
            hit_recursion = [False]

            # For a first pass we do a direct recursive calculation of the
            # property, but we block recursively visiting a value in the
            # computation of its property: When that happens, we simply
            # note that it happened and return the default value.
            def recur(strat):
                try:
                    return forced_value(strat)
                except AttributeError:
                    pass
                try:
                    result = mapping[strat]
                    if result is calculating:
                        hit_recursion[0] = True
                        return default
                    else:
                        return result
                except KeyError:
                    mapping[strat] = calculating
                    mapping[strat] = getattr(strat, calculation)(recur)
                    return mapping[strat]

            recur(self)

            # If we hit self-recursion in the computation of any strategy
            # value, our mapping at the end is imprecise - it may or may
            # not have the right values in it. We now need to proceed with
            # a more careful fixed point calculation to get the exact
            # values. Hopefully our mapping is still pretty good and it
            # won't take a large number of updates to reach a fixed point.
            if hit_recursion[0]:
                needs_update = set(mapping)

                # We track which strategies use which in the course of
                # calculating their property value. If A ever uses B in
                # the course of calculating its value, then whenveer the
                # value of B changes we might need to update the value of
                # A.
                listeners = defaultdict(set)
            else:
                needs_update = None

            count = 0
            seen = set()
            while needs_update:
                count += 1
                # If we seem to be taking a really long time to stabilize we
                # start tracking seen values to attempt to detect an infinite
                # loop. This should be impossible, and most code will never
                # hit the count, but having an assertion for it means that
                # testing is easier to debug and we don't just have a hung
                # test.
                # Note: This is actually covered, by test_very_deep_deferral
                # in tests/cover/test_deferred_strategies.py. Unfortunately it
                # runs into a coverage bug. See
                # https://bitbucket.org/ned/coveragepy/issues/605/
                # for details.
                if count > 50:  # pragma: no cover
                    key = frozenset(mapping.items())
                    assert key not in seen, (key, name)
                    seen.add(key)
                to_update = needs_update
                needs_update = set()
                for strat in to_update:
                    def recur(other):
                        try:
                            return forced_value(other)
                        except AttributeError:
                            pass
                        listeners[other].add(strat)
                        try:
                            return mapping[other]
                        except KeyError:
                            needs_update.add(other)
                            mapping[other] = default
                            return default

                    new_value = getattr(strat, calculation)(recur)
                    if new_value != mapping[strat]:
                        needs_update.update(listeners[strat])
                        mapping[strat] = new_value

            # We now have a complete and accurate calculation of the
            # property values for everything we have seen in the course of
            # running this calculation. We simultaneously update all of
            # them (not just the strategy we started out with).
            for k, v in mapping.items():
                setattr(k, cache_key, v)
            return getattr(self, cache_key)

        accept.__name__ = name
        return property(accept)

    # Returns True if this strategy can never draw a value and will always
    # result in the data being marked invalid.
    # The fact that this returns False does not guarantee that a valid value
    # can be drawn - this is not intended to be perfect, and is primarily
    # intended to be an optimisation for some cases.
    is_empty = recursive_property('is_empty', True)

    # Returns True if values from this strategy can safely be reused without
    # this causing unexpected behaviour.
    has_reusable_values = recursive_property('has_reusable_values', True)

    # Whether this strategy is suitable for holding onto in a cache.
    is_cacheable = recursive_property('is_cacheable', True)

    def calc_is_cacheable(self, recur):
        return True

    def calc_is_empty(self, recur):
        # Note: It is correct and significant that the default return value
        # from calc_is_empty is False despite the default value for is_empty
        # being true. The reason for this is that strategies should be treated
        # as empty absent evidence to the contrary, but most basic strategies
        # are trivially non-empty and it would be annoying to have to override
        # this method to show that.
        return False

    def calc_has_reusable_values(self, recur):
        return False

    def example(self, random=None):
        """Provide an example of the sort of value that this strategy
        generates. This is biased to be slightly simpler than is typical for
        values from this strategy, for clarity purposes.

        This method shouldn't be taken too seriously. It's here for interactive
        exploration of the API, not for any sort of real testing.

        This method is part of the public API.

        """
        context = _current_build_context.value
        if context is not None:
            if context.data is not None and context.data.depth > 0:
                note_deprecation(
                    'Using example() inside a strategy definition is a bad '
                    'idea. It will become an error in a future version of '
                    "Hypothesis, but it's unlikely that it's doing what you "
                    'intend even now. Instead consider using '
                    'hypothesis.strategies.builds() or '
                    '@hypothesis.strategies.composite to define your strategy.'
                    ' See '
                    'https://hypothesis.readthedocs.io/en/latest/data.html'
                    '#hypothesis.strategies.builds or '
                    'https://hypothesis.readthedocs.io/en/latest/data.html'
                    '#composite-strategies for more details.'
                )
            else:
                note_deprecation(
                    'Using example() inside a test function is a bad '
                    'idea. It will become an error in a future version of '
                    "Hypothesis, but it's unlikely that it's doing what you "
                    'intend even now. Instead consider using '
                    'hypothesis.strategies.data() to draw '
                    'more examples during testing. See '
                    'https://hypothesis.readthedocs.io/en/latest/data.html'
                    '#drawing-interactively-in-tests for more details.'
                )

        from hypothesis import find, settings, Verbosity

        # Conjecture will always try the zero example first. This would result
        # in us producing the same example each time, which is boring, so we
        # deliberately skip the first example it feeds us.
        first = []

        def condition(x):
            if first:
                return True
            else:
                first.append(x)
                return False
        try:
            return find(
                self,
                condition,
                random=random,
                settings=settings(
                    max_shrinks=0,
                    max_iterations=1000,
                    database=None,
                    verbosity=Verbosity.quiet,
                )
            )
        except (NoSuchExample, Unsatisfiable):
            # This can happen when a strategy has only one example. e.g.
            # st.just(x). In that case we wanted the first example after all.
            if first:
                return first[0]
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
            self.is_empty
            self.has_reusable_values
        except Exception:
            self.validate_called = False
            raise

    LABELS = {}

    @property
    def class_label(self):
        cls = self.__class__
        try:
            return cls.LABELS[cls]
        except KeyError:
            pass
        result = calc_label(cls)
        cls.LABELS[cls] = result
        return result

    @property
    def label(self):
        if self.__label is calculating:
            return 0
        if self.__label is None:
            self.__label = calculating
            self.__label = self.calc_label()
        return self.__label

    def calc_label(self):
        return self.class_label

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

    def calc_is_empty(self, recur):
        return all(recur(e) for e in self.original_strategies)

    def calc_has_reusable_values(self, recur):
        return all(recur(e) for e in self.original_strategies)

    def calc_is_cacheable(self, recur):
        return all(recur(e) for e in self.original_strategies)

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
            branch_labels = []
            shift = bit_length(len(pruned))
            for i, p in enumerate(pruned):
                branch_labels.append(
                    (((self.label ^ p.label) << shift) + i) & LABEL_MASK)
            self.__element_strategies = pruned
            self.__branch_labels = tuple(branch_labels)
        return self.__element_strategies

    @property
    def branch_labels(self):
        self.element_strategies
        return self.__branch_labels

    def calc_label(self):
        return combine_labels(self.class_label, *[
            p.label for p in self.original_strategies
        ])

    def do_draw(self, data):
        n = len(self.element_strategies)
        assert n > 0
        if n == 1:
            return data.draw(self.element_strategies[0])

        if self.sampler is None:
            i = cu.integer_range(data, 0, n - 1)
        else:
            i = self.sampler.sample(data)

        return data.draw(
            self.element_strategies[i], label=self.branch_labels[i])

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

    def calc_is_empty(self, recur):
        return recur(self.mapped_strategy)

    def calc_is_cacheable(self, recur):
        return recur(self.mapped_strategy)

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
                data.start_example()
                result = self.pack(data.draw(self.mapped_strategy))
                data.stop_example()
                return result
            except UnsatisfiedAssumption:
                data.stop_example(discard=True)
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

    def calc_is_empty(self, recur):
        return recur(self.filtered_strategy)

    def calc_is_cacheable(self, recur):
        return recur(self.filtered_strategy)

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
