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
import hypothesis.searchstrategy as strat
from hypothesis.types import RandomWithSeed
from hypothesis.searchstrategy import BuildContext, strategy
from hypothesis.internal.compat import hrange, text_type
from hypothesis.internal.fixers import nice_string, actually_equal
from hypothesis.internal.tracker import Tracker
from hypothesis.searchstrategy.numbers import BoundedIntStrategy, \
    FixedBoundedFloatStrategy, RandomGeometricIntStrategy
from hypothesis.searchstrategy.strategies import OneOfStrategy, \
    one_of_strategies


def test_string_strategy_produces_strings():
    strings = strategy(text_type)
    result = strings.produce_template(
        BuildContext(random), strings.produce_parameter(random))
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
    template = strat.draw_and_produce(BuildContext(random))
    for t in strat.simplify_such_that(template, lambda _: True):
        template = t
    return strat.reify(template)


def assert_minimizes_to(s, value):
    for _ in hrange(100):
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
    assert s.produce_template(
        BuildContext(random), s.draw_parameter(random)) == 'giving'
    simplifications = list(s.simplify_such_that('giving', lambda _: True))
    assert len(simplifications) == 1
    assert simplifications[0] == 'giving'


Litter = namedtuple('Litter', ('kitten1', 'kitten2'))


def test_named_tuples_always_produce_named_tuples():
    s = strategy(Litter(int, int))

    for i in hrange(100):
        assert isinstance(
            s.produce_template(
                BuildContext(random), s.produce_parameter(random)), Litter)

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


@strategy.extend(X)
class XStrategy(strat.MappedSearchStrategy):
    pass


@strategy.extend(X)
def define_x_strategy(descriptor, settings):
    return XStrategy(
        strategy=strategy(descriptor.x, settings),
        descriptor=descriptor,
    )


def test_strategy_repr_handles_custom_types():
    assert 'X(x=int)' in repr(strategy(X(int)))


class TrivialStrategy(strat.SearchStrategy):

    def __init__(self, descriptor):
        self.descriptor = descriptor


def test_float_strategy_does_not_overflow():
    s = strategy(float)

    for _ in hrange(100):
        s.produce_template(BuildContext(random), s.produce_parameter(random))


def test_does_not_shrink_tuple_length():
    assert_minimizes_to((bool,), (False,))


def test_or_errors_when_given_non_strategy():
    bools = strategy((bool,))
    with pytest.raises(ValueError):
        bools | 'foo'


def test_joining_zero_strategies_fails():
    with pytest.raises(ValueError):
        one_of_strategies(())


def test_directly_joining_one_strategy_also_fails():
    with pytest.raises(ValueError):
        OneOfStrategy([RandomGeometricIntStrategy()])


def test_list_strategy_reprs_as_list():
    x = strategy([int])
    assert repr(x) == 'ListStrategy([int])'


SomeNamedTuple = namedtuple('SomeNamedTuple', ('a', 'b'))


def test_strategy_for_integer_range_produces_only_integers_in_that_range():
    just_one_integer = strategy(descriptors.IntegerRange(1, 1))
    for _ in hrange(100):
        pv = just_one_integer.draw_parameter(random)
        x = just_one_integer.produce_template(BuildContext(random), pv)
        assert x == 1
    some_integers = strategy(descriptors.IntegerRange(1, 10))
    for _ in hrange(100):
        pv = some_integers.produce_parameter(random)
        x = some_integers.produce_template(BuildContext(random), pv)
        assert 1 <= x <= 10


def test_strategy_for_integer_range_can_produce_end_points():
    some_integers = strategy(descriptors.IntegerRange(1, 10))
    found = set()
    for _ in hrange(1000):  # pragma: no branch
        pv = some_integers.produce_parameter(random)
        x = some_integers.produce_template(BuildContext(random), pv)
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
    some_integers = strategy(descriptors.IntegerRange(1, 10))

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
        BoundedIntStrategy(10, 9)


def test_does_not_simplify_outside_range():
    n = 3
    s = BoundedIntStrategy(0, n)
    for t in s.simplify(n):
        assert 0 <= t <= n


def test_random_repr_has_seed():
    strat = strategy(random.Random)
    rnd = strat.reify(
        strat.produce_template(BuildContext(random.Random()), None))
    seed = rnd.seed
    assert text_type(seed) in repr(rnd)


def test_random_only_produces_special_random():
    st = strategy(random.Random)
    assert isinstance(
        st.reify(st.produce_template(
            BuildContext(random), st.draw_parameter(random))),
        RandomWithSeed
    )


def test_randoms_with_same_seed_are_equal():
    s = RandomWithSeed(123)
    t = RandomWithSeed(123)
    assert s == t
    s.random()
    assert s == t
    t.random()
    assert s == t
    assert t != RandomWithSeed(124)


def test_just_strategy_uses_repr():
    class WeirdRepr(object):

        def __repr__(self):
            return 'ABCDEFG'

    assert repr(
        strategy(descriptors.just(WeirdRepr()))
    ) == 'JustStrategy(value=%r)' % (WeirdRepr(),)


def test_fixed_bounded_float_strategy_converts_its_args():
    st = FixedBoundedFloatStrategy(0, 1)
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
    assert nice_string(x) == nice_string(x)


class AwkwardDict(dict):

    def items(self):
        results = list(super(AwkwardDict, self).items())
        random.shuffle(results)
        for r in results:
            yield r


def test_dict_descriptor_representation_is_stable_for_order():
    x = AwkwardDict({i: i for i in hrange(100)})
    assert nice_string(x) == nice_string(x)


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


def test_can_map():
    s = strategy(int).map(pack=lambda t: "foo", descriptor="foo")
    assert s.example() == "foo"
