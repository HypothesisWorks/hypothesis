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
from hypothesis.specifiers import Dictionary
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

    def strictly_simpler(self, x, y):
        for i, (u, v) in enumerate(zip(x, y)):
            s = self.element_strategies[i]
            if s.strictly_simpler(u, v):
                return True
            if s.strictly_simpler(v, u):
                return False
        return False

    def simplifier_for_index(self, i, simplifier):
        def accept(random, template):
            assert len(template) == len(self.element_strategies)
            replacement = list(template)
            for s in simplifier(random, template[i]):
                replacement[i] = s
                yield tuple(replacement)
        accept.__name__ = str(
            'simplifier_for_index(%d, %s)' % (i, simplifier.__name__)
        )
        return accept

    def simplifiers(self, random, template):
        if not template:
            return
        for i in hrange(len(self.element_strategies)):
            strat = self.element_strategies[i]
            for simplifier in strat.simplifiers(random, template[i]):
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

    def simplifiers(self, random, template):
        if not self.element_strategy:
            return
        if not template:
            return

        if len(template) <= 1:
            yield self.simplify_to_empty
        yield self.simplify_with_random_discards
        yield self.simplify_with_example_cloning
        yield self.simplify_arrange_by_pivot
        yield self.simplify_with_single_deletes
        yield self.simplify_to_singletons

        for simplify in self.element_strategy.simplifiers(
            random,
            template[0]
        ):
            yield self.shared_simplification(simplify)

        for i in self.indices_roughly_from_worst_to_best(random, template):
            yield self.simplifier_for_index(
                i, self.element_strategy.full_simplify)

    def simplifier_for_index(self, i, simplify):
        def accept(random, template):
            if i >= len(template):
                return
            replacement = list(template)
            for s in simplify(random, template[i]):
                replacement[i] = s
                yield tuple(replacement)
        accept.__name__ = str(
            'simplifier_for_index(%d, %s)' % (i, simplify.__name__)
        )
        return accept

    def simplify_to_empty(self, random, x):
        assert isinstance(x, tuple)
        if not x:
            return

        yield ()

    def simplify_to_singletons(self, random, x):
        for t in x:
            yield (t,)

    def strictly_simpler(self, x, y):
        if len(x) > len(y):
            return False
        if len(x) < len(y):
            return True
        if not x:
            return False
        for u, v in zip(x, y):
            if self.element_strategy.strictly_simpler(u, v):
                return True
            if self.element_strategy.strictly_simpler(v, u):
                return False
        return False

    def simplify_arrange_by_pivot(self, random, x):
        if len(x) <= 1:
            return
        for _ in hrange(10):
            pivot = random.choice(x)
            left = []
            center = []
            right = []
            simpler = self.element_strategy.strictly_simpler
            for y in x:
                if simpler(y, pivot):
                    left.append(y)
                elif simpler(pivot, y):
                    right.append(y)
                else:
                    center.append(y)
            bits = list(map(tuple, (left, center, right)))
            for t in bits:
                if t and len(t) < len(x):
                    yield tuple(t)

    def simplify_with_example_cloning(self, random, x):
        assert isinstance(x, tuple)
        if len(x) <= 1:
            return

        best = x[0]
        any_shrinks = False
        for t in x:
            if self.element_strategy.strictly_simpler(
                t, best
            ):
                any_shrinks = True
                best = t
            if not any_shrinks:
                any_shrinks = self.element_strategy.strictly_simpler(best, t)

        if any_shrinks:
            yield (best,) * len(x)

        for _ in hrange(20):
            result = list(x)
            pivot = random.choice(x)
            for _ in hrange(10):
                new_pivot = random.choice(x)
                if self.element_strategy.strictly_simpler(new_pivot, pivot):
                    pivot = new_pivot
            indices = [
                j for j in hrange(len(x))
                if self.element_strategy.strictly_simpler(pivot, x[j])]
            if not indices:
                break
            random.shuffle(indices)
            indices = indices[:random.randint(1, len(x) - 1)]
            for j in indices:
                result[j] = pivot
            yield tuple(result)

    def simplify_with_random_discards(self, random, x):
        assert isinstance(x, tuple)
        if len(x) <= 3:
            return

        for _ in hrange(10):
            results = []
            for t in x:
                if random.randint(0, 1):
                    results.append(t)
            yield tuple(results)

    def indices_roughly_from_worst_to_best(self, random, x):
        pivot = random.choice(x)
        bad = []
        good = []
        y = list(hrange(len(x)))
        random.shuffle(y)
        for t in y:
            if self.element_strategy.strictly_simpler(x[t], pivot):
                good.append(t)
            else:
                bad.append(t)
        return bad + good

    def simplify_with_single_deletes(self, random, x):
        assert isinstance(x, tuple)
        if len(x) <= 1:
            return

        for i in self.indices_roughly_from_worst_to_best(random, x):
            y = list(x)
            del y[i]
            yield tuple(y)

    def shared_indices(self, template):
        same_valued_indices = {}
        for i, value in enumerate(template):
            same_valued_indices.setdefault(value, []).append(i)
        for indices in same_valued_indices.values():
            if len(indices) > 1:
                yield tuple(indices)

    def shared_simplification(self, simplify):
        def accept(random, x):
            sharing = list(self.shared_indices(x))
            if not sharing:
                return
            sharing.sort(key=len, reverse=True)

            for indices in sharing:
                value = x[indices[0]]
                for simpler in simplify(random, value):
                    copy = list(x)
                    for i in indices:
                        copy[i] = simpler
                    yield tuple(copy)
        accept.__name__ = str(
            'shared_simplification(%s)' % (simplify.__name__,)
        )
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

    def convert_template(self, template):
        seen = set()
        deduped = []
        for x in template:
            if x not in seen:
                seen.add(x)
                deduped.append(x)
        if self.list_strategy.element_strategy:
            simpler = self.list_strategy.element_strategy.strictly_simpler
            for i in hrange(1, len(deduped)):
                j = i
                while j > 0:
                    if simpler(deduped[j], deduped[j - 1]):
                        deduped[j - 1], deduped[j] = deduped[j], deduped[j - 1]
                        j -= 1
                    else:
                        break
        return tuple(deduped)

    def produce_template(self, context, pv):
        return self.convert_template(
            (self.list_strategy.produce_template(context, pv)))

    def strictly_simpler(self, x, y):
        return self.list_strategy.strictly_simpler(x, y)

    def convert_simplifier(self, simplifier):
        def accept(random, template):
            for value in simplifier(random, tuple(template)):
                yield self.convert_template(value)
        accept.__name__ = simplifier.__name__
        return accept

    def simplifiers(self, random, template):
        for simplify in self.list_strategy.simplifiers(random, template):
            yield self.convert_simplifier(simplify)

    def to_basic(self, value):
        result = self.list_strategy.to_basic(value)
        result.sort()
        return result

    def from_basic(self, value):
        check_data_type(list, value)
        return self.convert_template(self.list_strategy.from_basic(value))


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


@strategy.extend(Dictionary)
def define_dictionary_strategy(specifier, settings):
    return strategy(
        [(specifier.keys, specifier.values)], settings
    ).map(specifier.dict_class)
