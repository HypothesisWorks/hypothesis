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
from hypothesis.utils.show import show
from hypothesis.internal.compat import hrange
from hypothesis.searchstrategy.strategies import SearchStrategy, \
    MappedSearchStrategy, strategy, check_type, check_length, \
    check_data_type, one_of_strategies


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
        self.element_strategies = strategies
        self.size_lower_bound = 1
        self.size_upper_bound = 1
        for e in self.element_strategies:
            self.size_lower_bound *= e.size_lower_bound
            self.size_upper_bound *= e.size_upper_bound

    def reify(self, value):
        return self.newtuple(
            e.reify(v) for e, v in zip(self.element_strategies, value)
        )

    def __repr__(self):
        if len(self.element_strategies) == 1:
            tuple_string = '%s,' % (repr(self.element_strategies[0]),)
        else:
            tuple_string = ', '.join(map(repr, self.element_strategies))
        return 'TupleStrategy((%s), %s)' % (
            tuple_string, self.tuple_type.__name__
        )

    def newtuple(self, xs):
        """Produce a new tuple of the correct type."""
        if self.tuple_type == tuple:
            return tuple(xs)
        else:
            return self.tuple_type(*xs)

    def produce_parameter(self, random):
        return tuple(
            e.draw_parameter(random)
            for e in self.element_strategies
        )

    def produce_template(self, context, pv):
        es = self.element_strategies
        return self.newtuple([
            g.draw_template(context, v)
            for g, v in zip(es, pv)
        ])

    def simplifier_for_index(self, i, simplifier):
        def accept(template):
            replacement = list(template)
            for s in simplifier(template[i]):
                replacement[i] = s
                yield tuple(replacement)
        return accept

    def simplifiers(self):
        for i in hrange(len(self.element_strategies)):
            strat = self.element_strategies[i]
            for simplifier in strat.simplifiers():
                yield self.simplifier_for_index(i, simplifier)

    def to_basic(self, value):
        return [
            f.to_basic(v)
            for f, v in zip(self.element_strategies, value)
        ]

    def from_basic(self, value):
        check_length(len(self.element_strategies), value)
        return self.newtuple(
            f.from_basic(v)
            for f, v in zip(self.element_strategies, value)
        )


class ListStrategy(SearchStrategy):

    """A strategy for lists which takes an intended average length and a
    strategy for each of its element types and generates lists containing any
    of those element types.

    The conditional distribution of the length is geometric, and the
    conditional distribution of each parameter is whatever their
    strategies define.

    """

    Parameter = namedtuple(
        'Parameter', ('child_parameter', 'average_length')
    )

    def __init__(self,
                 strategies, average_length=50.0):
        SearchStrategy.__init__(self)

        self.average_length = average_length
        strategies = tuple(strategies)
        if strategies:
            self.element_strategy = one_of_strategies(strategies)
        else:
            self.element_strategy = None
            self.size_upper_bound = 1
            self.size_lower_bound = 1

    def reify(self, value):
        if self.element_strategy is not None:
            return list(map(self.element_strategy.reify, value))
        else:
            return []

    def __repr__(self):
        return 'ListStrategy(%r)' % (
            self.element_strategy,
        )

    def produce_parameter(self, random):
        if self.element_strategy is None:
            return None
        else:
            return self.Parameter(
                average_length=random.expovariate(
                    1.0 / self.average_length),
                child_parameter=self.element_strategy.draw_parameter(random),
            )

    def produce_template(self, context, pv):
        if self.element_strategy is None:
            return ()
        length = dist.geometric(context.random, 1.0 / (1 + pv.average_length))
        result = []
        for _ in hrange(length):
            result.append(
                self.element_strategy.draw_template(
                    context, pv.child_parameter))
        return tuple(result)

    def simplifiers(self):
        if not self.element_strategy:
            return

        yield self.simplify_lengthwise

        for simplify in self.element_strategy.simplifiers():
            yield self.shared_simplification(simplify)

        for simplify in self.element_strategy.simplifiers():
            yield self.simplify_elementwise(simplify)

    def simplify_lengthwise(self, x):
        assert isinstance(x, tuple)
        if not x:
            return

        yield ()

        if len(x) > 3:
            mid = len(x) // 2
            yield x[:mid]
            yield x[mid:]

        if len(x) > 1:
            for i in hrange(0, len(x)):
                y = list(x)
                del y[i]
                yield tuple(y)

        for i in hrange(0, len(x) - 1):
            z = list(x)
            del z[i]
            del z[i]
            yield tuple(z)

    def shared_simplification(self, simplify):
        def accept(x):
            same_valued_indices = {}
            for i, value in enumerate(x):
                same_valued_indices.setdefault(value, []).append(i)
            for indices in same_valued_indices.values():
                if len(indices) > 1:
                    value = x[indices[0]]
                    for simpler in simplify(value):
                        copy = list(x)
                        for i in indices:
                            copy[i] = simpler
                        yield tuple(copy)
        return accept

    def simplify_elementwise(self, simplify):
        def accept(x):
            for i in hrange(0, len(x)):
                for s in simplify(x[i]):
                    z = list(x)
                    z[i] = s
                    yield tuple(z)
        return accept

    def to_basic(self, value):
        check_type(tuple, value)
        if self.element_strategy is None:
            return []
        return list(map(self.element_strategy.to_basic, value))

    def from_basic(self, value):
        check_data_type(list, value)
        if self.element_strategy is None:
            return ()
        return tuple(map(self.element_strategy.from_basic, value))


class SetStrategy(SearchStrategy):

    """A strategy for sets of values, defined in terms of a strategy for lists
    of values."""

    Parameter = namedtuple(
        'Parameter',
        ('stopping_chance', 'child_parameter'),
    )

    def __repr__(self):
        return 'SetStrategy(list_strategy=%r)' % (
            self.list_strategy,
        )

    def __init__(self, strategies, average_length=50.0):
        self.list_strategy = ListStrategy(strategies, average_length)

        def powset(n):
            if n >= 32:
                return float('inf')
            return 2 ** n

        elements = self.list_strategy.element_strategy

        if not elements:
            self.size_lower_bound = 1
            self.size_upper_bound = 1
        else:
            self.size_lower_bound = powset(elements.size_lower_bound)
            self.size_upper_bound = powset(elements.size_upper_bound)

    def reify(self, value):
        return set(self.list_strategy.reify(tuple(value)))

    def produce_parameter(self, random):
        return self.list_strategy.produce_parameter(random)

    def produce_template(self, context, pv):
        return frozenset(self.list_strategy.produce_template(context, pv))

    def convert_simplifier(self, simplifier):
        def accept(template):
            for value in simplifier(tuple(template)):
                yield frozenset(value)
        return accept

    def simplifiers(self):
        for simplify in self.list_strategy.simplifiers():
            yield self.convert_simplifier(simplify)

    def to_basic(self, value):
        check_type(frozenset, value)
        result = self.list_strategy.to_basic(tuple(value))
        result.sort()
        return result

    def from_basic(self, value):
        check_data_type(list, value)
        return frozenset(self.list_strategy.from_basic(value))


class FrozenSetStrategy(MappedSearchStrategy):

    """A strategy for frozensets of values, defined in terms of a strategy for
    lists of values."""

    def __init__(self, set_strategy):
        super(FrozenSetStrategy, self).__init__(
            strategy=set_strategy,
            pack=frozenset,
        )

    def __repr__(self):
        return 'FrozenSetStrategy(%r)' % (self.mapped_strategy,)


class FixedKeysDictStrategy(MappedSearchStrategy):

    """A strategy which produces dicts with a fixed set of keys, given a
    strategy for each of their equivalent values.

    e.g. {'foo' : some_int_strategy} would
    generate dicts with the single key 'foo' mapping to some integer.

    """

    def __init__(self, strategy_dict):
        self.keys = tuple(sorted(
            strategy_dict.keys(), key=show
        ))
        super(FixedKeysDictStrategy, self).__init__(
            strategy=TupleStrategy(
                (strategy_dict[k] for k in self.keys), tuple
            )
        )

    def __repr__(self):
        return 'FixedKeysDictStrategy(%r, %r)' % (
            self.keys, self.mapped_strategy)

    def pack(self, value):
        return dict(zip(self.keys, value))


@strategy.extend(set)
def define_set_strategy(specifier, settings):
    return SetStrategy(
        (strategy(d, settings) for d in specifier),
        average_length=settings.average_list_length
    )


@strategy.extend(frozenset)
def define_frozen_set_strategy(specifier, settings):
    return FrozenSetStrategy(strategy(set(specifier), settings))


@strategy.extend(list)
def define_list_strategy(specifier, settings):
    return ListStrategy(
        [strategy(d, settings) for d in specifier],
        average_length=settings.average_list_length
    )

Settings.define_setting(
    'average_list_length',
    default=50.0,
    description='Average length of lists to use'
)


@strategy.extend(tuple)
def define_tuple_strategy(specifier, settings):
    return TupleStrategy(
        tuple(strategy(d, settings) for d in specifier),
        tuple_type=type(specifier)
    )


@strategy.extend(dict)
def define_dict_strategy(specifier, settings):
    strategy_dict = {}
    for k, v in specifier.items():
        strategy_dict[k] = strategy(v, settings)
    return FixedKeysDictStrategy(strategy_dict)
