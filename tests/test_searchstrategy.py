# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import math
import random
from collections import namedtuple

import pytest
import hypothesis.descriptors as descriptors
import hypothesis.strategytable as ss
import hypothesis.searchstrategy as strat
from hypothesis.internal.compat import hrange, text_type
from hypothesis.internal.tracker import Tracker
from hypothesis.internal.utils.fixers import actually_equal


def strategy(*args, **kwargs):
    return ss.StrategyTable().strategy(*args, **kwargs)


def test_string_strategy_produces_strings():
    strings = strategy(text_type)
    result = strings.produce_template(random, strings.parameter.draw(random))
    assert result is not None


def test_unary_tuple_strategy_has_trailing_comma():
    assert repr(strategy((int,))) == 'TupleStrategy((int,))'


Blah = namedtuple('Blah', ('hi',))


def test_named_tuple_strategy_has_tuple_in_name_and_no_trailing_comma():
    assert repr(strategy(Blah(int))) == 'TupleStrategy(Blah(hi=int))'


def test_class_names_are_simplified_in_sets():
    assert repr(strategy({float})) == 'SetStrategy({float})'


def alternating(*args):
    return strategy(descriptors.one_of(args))


def some_minimal_element(s):
    strat = strategy(s)
    template = strat.draw_and_produce(random)
    for t in strat.simplify_such_that(template, lambda _: True):
        template = t
    return strat.reify(template)


def assert_minimizes_to(s, value):
    for _ in xrange(100):
        m = some_minimal_element(s)
        if actually_equal(m, value):
            return
    assert False


def test_can_minimize_component_types():
    ios = alternating(text_type, int)
    assert_minimizes_to(ios, '')
    assert_minimizes_to(ios, 0)


def test_can_minimize_tuples():
    assert_minimizes_to((int, int, int), (0, 0, 0))


def assert_no_duplicates_in_simplify(s, x):
    s = strategy(s)
    t = Tracker()
    t.track(x)
    for y in s.simplify(x):
        assert t.track(y) == 1


def test_ints_no_duplicates_in_simplify():
    assert_no_duplicates_in_simplify(int, 555)


def test_int_lists_no_duplicates_in_simplify():
    assert_no_duplicates_in_simplify([int], (0, 555, 1281))


def test_just_works():
    s = strategy(descriptors.just('giving'))
    assert s.produce_template(random, s.parameter.draw(random)) == 'giving'
    simplifications = list(s.simplify_such_that('giving', lambda _: True))
    assert len(simplifications) == 1
    assert simplifications[0] == 'giving'


Litter = namedtuple('Litter', ('kitten1', 'kitten2'))


def test_named_tuples_always_produce_named_tuples():
    s = strategy(Litter(int, int))

    for i in hrange(100):
        assert isinstance(
            s.produce_template(random, s.parameter.draw(random)), Litter)

    for x in s.simplify(Litter(100, 100)):
        assert isinstance(x, Litter)


def test_simplifying_something_that_does_not_satisfy_errors():
    s = strategy(int)
    f = lambda x: x > 100
    with pytest.raises(ValueError):
        next(s.simplify_such_that(1, f))


def test_strategy_repr_handles_dicts():
    s = repr(strategy({'foo': int, 'bar': str}))
    assert 'foo' in s
    assert 'bar' in s
    assert 'int' in s
    assert 'str' in s


def test_strategy_repr_handles_tuples():
    s = repr(strategy((str, str)))
    assert '(str, str)' in s


def test_strategy_repr_handles_bools():
    s = repr(strategy(bool))
    assert '(bool)' in s


class X(object):

    def __init__(self, x):
        self.x = x


@ss.strategy_for_instances(X)
class XStrategy(strat.MappedSearchStrategy):
    pass


@ss.strategy_for_instances(X)
def define_x_strategy(strategies, descriptor):
    return XStrategy(
        strategy=strategies.strategy(descriptor.x),
        descriptor=descriptor,
    )


def test_strategy_repr_handles_custom_types():
    assert 'X(x=int)' in repr(ss.StrategyTable().strategy(X(int)))


class TrivialStrategy(strat.SearchStrategy):

    def __init__(self, descriptor):
        self.descriptor = descriptor


def test_strategy_repr_handles_instances_without_dicts():
    strats = ss.StrategyTable()
    strats.define_specification_for_instances(
        int, lambda s, d: TrivialStrategy(d))

    assert repr(strats.strategy(42)) == 'TrivialStrategy(42)'
    assert repr(strats.strategy(23)) == 'TrivialStrategy(23)'


def test_float_strategy_does_not_overflow():
    strategy = ss.StrategyTable().strategy(float)

    for _ in hrange(100):
        strategy.produce_template(random, strategy.parameter.draw(random))


def test_does_not_shrink_tuple_length():
    assert_minimizes_to((bool,), (False,))


def test_or_errors_when_given_non_strategy():
    bools = ss.StrategyTable().strategy((bool,))
    with pytest.raises(ValueError):
        bools | 'foo'


def test_joining_zero_strategies_fails():
    with pytest.raises(ValueError):
        strat.one_of_strategies(())


def test_directly_joining_one_strategy_also_fails():
    with pytest.raises(ValueError):
        strat.OneOfStrategy([strat.RandomGeometricIntStrategy()])


def test_list_strategy_reprs_as_list():
    x = ss.StrategyTable.default().strategy([int])
    assert repr(x) == 'ListStrategy([int])'


SomeNamedTuple = namedtuple('SomeNamedTuple', ('a', 'b'))


def test_strategy_for_integer_range_produces_only_integers_in_that_range():
    table = ss.StrategyTable()
    just_one_integer = table.strategy(descriptors.IntegerRange(1, 1))
    for _ in hrange(100):
        pv = just_one_integer.parameter.draw(random)
        x = just_one_integer.produce_template(random, pv)
        assert x == 1
    some_integers = table.strategy(descriptors.IntegerRange(1, 10))
    for _ in hrange(100):
        pv = some_integers.parameter.draw(random)
        x = some_integers.produce_template(random, pv)
        assert 1 <= x <= 10


def test_strategy_for_integer_range_can_produce_end_points():
    table = ss.StrategyTable()
    some_integers = table.strategy(descriptors.IntegerRange(1, 10))
    found = set()
    for _ in hrange(1000):  # pragma: no branch
        pv = some_integers.parameter.draw(random)
        x = some_integers.produce_template(random, pv)
        found.add(x)
        if 1 in found and 10 in found:
            break
    else:
        assert False  # pragma: no cover
    assert 1 in found
    assert 10 in found


def last(xs):
    t = None
    for x in xs:
        t = x
    return t


def test_simplify_integer_range_can_push_to_near_boundaries():
    table = ss.StrategyTable()
    some_integers = table.strategy(descriptors.IntegerRange(1, 10))

    predicates = [
        (lambda x: True, 1),
        (lambda x: x > 1, 2),
        (lambda x: x > 5, 10),
        (lambda x: x > 5 and x < 10, 9),
    ]

    for p, v in predicates:
        some = False
        for i in hrange(1, 10):
            if p(i):
                some = True
                assert last(some_integers.simplify_such_that(i, p)) == v
        assert some


def test_rejects_invalid_ranges():
    with pytest.raises(ValueError):
        strat.BoundedIntStrategy(10, 9)


def test_does_not_simplify_outside_range():
    n = 3
    s = strat.BoundedIntStrategy(0, n)
    for t in s.simplify(n):
        assert 0 <= t <= n


def test_random_repr_has_seed():
    strat = strategy(random.Random)
    rnd = strat.reify(strat.produce_template(random.Random(), None))
    seed = rnd.seed
    assert text_type(seed) in repr(rnd)


def test_random_only_produces_special_random():
    st = strategy(random.Random)
    assert isinstance(
        st.reify(st.produce_template(random, st.parameter.draw(random))),
        strat.RandomWithSeed
    )


def test_randoms_with_same_seed_are_equal():
    s = strat.RandomWithSeed(123)
    t = strat.RandomWithSeed(123)
    assert s == t
    s.random()
    assert s == t
    t.random()
    assert s == t
    assert t != strat.RandomWithSeed(124)


def test_just_strategy_uses_repr():
    class WeirdRepr(object):

        def __repr__(self):
            return 'ABCDEFG'

    assert repr(
        strategy(descriptors.just(WeirdRepr()))
    ) == 'JustStrategy(value=%r)' % (WeirdRepr(),)


def test_fixed_bounded_float_strategy_converts_its_args():
    st = strat.FixedBoundedFloatStrategy(0, 1)
    for t in st.simplify(0.5):
        assert isinstance(t, float)


class AwkwardSet(set):

    def __iter__(self):
        results = list(super(AwkwardSet, self).__iter__())
        random.shuffle(results)
        for r in results:
            yield r


def test_set_descriptor_representation_is_stable_for_order():
    x = AwkwardSet(list(hrange(100)))
    assert repr(x) != repr(x)
    assert strat.nice_string(x) == strat.nice_string(x)


class AwkwardDict(dict):

    def items(self):
        results = list(super(AwkwardDict, self).items())
        random.shuffle(results)
        for r in results:
            yield r


def test_dict_descriptor_representation_is_stable_for_order():
    x = AwkwardDict({i: i for i in hrange(100)})
    assert strat.nice_string(x) == strat.nice_string(x)


def test_example_augmented_strategy_decomposes_as_main():
    s = strat.ExampleAugmentedStrategy(
        main_strategy=strategy((int,)),
        examples=[(1,)],
    )
    assert list(s.decompose((1,))) == [(int, 1)]
    assert list(s.decompose((2,))) == [(int, 2)]


def test_can_simplify_nan():
    s = strategy(float)
    x = list(s.simplify_such_that(float('nan'), math.isnan))[-1]
    assert math.isnan(x)


def test_can_simplify_tuples_of_nan():
    s = strategy((float,))
    x = list(
        s.simplify_such_that((float('nan'),), lambda x: math.isnan(x[0])))[-1]
    assert math.isnan(x[0])


def test_nan_is_not_simpler_than_nan():
    s = strategy(float)
    simpler = list(s.simplify(float('nan')))
    for x in simpler:
        assert not math.isnan(x)


def test_infinity_simplifies_to_finite():
    s = strategy(float)
    assert list(
        s.simplify_such_that(float('inf'), lambda x: x >= 1))[-1] == 1.0
    assert list(
        s.simplify_such_that(float('-inf'), lambda x: x <= -1))[-1] == -1.0


def test_one_of_descriptor_distinguishes_sets_and_frozensets():
    d = descriptors.one_of(({int}, frozenset({int})))
    s = strategy(d)
    assert s.descriptor == d


def test_minimizing_a_very_large_int_produces_an_int():
    s = strategy(int)
    shrunk = list(s.simplify_such_that(1 << 73, lambda x: x > 1))[-1]
    assert type(shrunk) == int


def test_does_not_shrink_size_for_non_hashable_sample():
    s = strategy(descriptors.sampled_from(([], [])))
    assert s.size_lower_bound == 2
    assert s.size_upper_bound == 2

