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
import hypothesis.specifiers as specifiers
from hypothesis.types import RandomWithSeed
from hypothesis.internal.compat import hrange, text_type
from hypothesis.searchstrategy.numbers import BoundedIntStrategy, \
    FixedBoundedFloatStrategy, RandomGeometricIntStrategy
from hypothesis.searchstrategy.strategies import BuildContext, \
    OneOfStrategy, strategy, one_of_strategies


def test_string_strategy_produces_strings():
    strings = strategy(text_type)
    result = strings.produce_template(
        BuildContext(random), strings.produce_parameter(random))
    assert result is not None


Blah = namedtuple('Blah', ('hi',))


def alternating(*args):
    return strategy(specifiers.one_of(args))


def some_minimal_element(s):
    strat = strategy(s)
    template = strat.draw_and_produce(BuildContext(random))
    for t in strat.simplify_such_that(template, lambda _: True):
        template = t
    return strat.reify(template)


def assert_minimizes_to(s, value):
    for _ in hrange(100):
        m = some_minimal_element(s)
        if m == value:
            return
    assert False


def test_can_minimize_component_types():
    ios = alternating(text_type, int)
    assert_minimizes_to(ios, '')
    assert_minimizes_to(ios, 0)


def test_can_minimize_tuples():
    assert_minimizes_to((int, int, int), (0, 0, 0))


def test_just_works():
    s = strategy(specifiers.just('giving'))
    assert s.example() == 'giving'


def test_simplifying_something_that_does_not_satisfy_errors():
    s = strategy(int)
    f = lambda x: x > 100
    with pytest.raises(ValueError):
        next(s.simplify_such_that(1, f))


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

SomeNamedTuple = namedtuple('SomeNamedTuple', ('a', 'b'))


def test_strategy_for_integer_range_produces_only_integers_in_that_range():
    just_one_integer = strategy(specifiers.IntegerRange(1, 1))
    for _ in hrange(100):
        pv = just_one_integer.draw_parameter(random)
        x = just_one_integer.produce_template(BuildContext(random), pv)
        assert x == 1
    some_integers = strategy(specifiers.IntegerRange(1, 10))
    for _ in hrange(100):
        pv = some_integers.produce_parameter(random)
        x = some_integers.produce_template(BuildContext(random), pv)
        assert 1 <= x <= 10


def test_strategy_for_integer_range_can_produce_end_points():
    some_integers = strategy(specifiers.IntegerRange(1, 10))
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
    some_integers = strategy(specifiers.IntegerRange(1, 10))

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
    for t in s.full_simplify(n):
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


def test_just_strategy_uses_repr():
    class WeirdRepr(object):

        def __repr__(self):
            return 'ABCDEFG'

    assert repr(
        strategy(specifiers.just(WeirdRepr()))
    ) == 'JustStrategy(value=%r)' % (WeirdRepr(),)


def test_fixed_bounded_float_strategy_converts_its_args():
    st = FixedBoundedFloatStrategy(0, 1)
    for t in st.full_simplify(0.5):
        assert isinstance(t, float)


class AwkwardSet(set):

    def __iter__(self):
        results = list(super(AwkwardSet, self).__iter__())
        random.shuffle(results)
        for r in results:
            yield r


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
    simpler = list(s.full_simplify(float('nan')))
    for x in simpler:
        assert not math.isnan(x)


def test_infinity_simplifies_to_finite():
    s = strategy(float)
    assert list(
        s.simplify_such_that(float('inf'), lambda x: x >= 1))[-1] == 1.0
    assert list(
        s.simplify_such_that(float('-inf'), lambda x: x <= -1))[-1] == -1.0


def test_minimizing_a_very_large_int_produces_an_int():
    s = strategy(int)
    shrunk = list(s.simplify_such_that(1 << 73, lambda x: x > 1))[-1]
    assert type(shrunk) == int


def test_does_not_shrink_size_for_non_hashable_sample():
    s = strategy(specifiers.sampled_from(([], [])))
    assert s.size_lower_bound == 2
    assert s.size_upper_bound == 2


def test_can_map():
    s = strategy(int).map(pack=lambda t: 'foo')
    assert s.example() == 'foo'


def test_sample_from_empty_errors():
    with pytest.raises(ValueError):
        strategy(specifiers.sampled_from([]))
