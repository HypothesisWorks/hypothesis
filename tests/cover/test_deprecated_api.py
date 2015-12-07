# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import sys
from random import Random
from decimal import Decimal
from fractions import Fraction
from collections import namedtuple

import pytest

import hypothesis.specifiers as s
import hypothesis.strategies as st
from hypothesis import find, Settings, strategy
from hypothesis.errors import InvalidArgument
from tests.common.basic import Bitfields
from hypothesis.internal.compat import text_type, binary_type, \
    integer_types
from hypothesis.searchstrategy.narytree import Leaf, Branch, NAryTree

original_profile = Settings.default

Settings.register_profile(
    'nonstrict', Settings(strict=False)
)


def setup_function(fn):
    Settings.load_profile('nonstrict')


def teardown_function(fn):
    Settings.load_profile('default')


@pytest.mark.parametrize(u'typ', [
    complex, float, bool, Random, type(None), text_type, binary_type,
    Decimal, Fraction,
])
def test_types_give_types(typ):
    assert isinstance(strategy(typ).example(), typ)


def test_int_gives_ints():
    assert isinstance(strategy(int).example(), integer_types)


def test_just_is_just():
    assert strategy(s.just(1)).example() == 1


def test_can_extend_strategy():
    class Foo(object):
        pass

    @strategy.extend(Foo)
    def s(foo, settings):
        return st.booleans()

    @strategy.extend_static(Foo)
    def t(foo, settings):
        return st.text()
    assert isinstance(strategy(Foo()).example(), bool)
    assert isinstance(strategy(Foo).example(), text_type)


def test_tuples_give_tuples():
    x = strategy((bool, bool)).example()
    assert len(x) == 2
    assert isinstance(x[0], bool)
    assert isinstance(x[1], bool)


def test_lists_mix():
    x = strategy([(bool,), (bool, bool)]).example()
    assert all(1 <= len(y) <= 2 for y in x)


def test_none_lists():
    assert not any(strategy([None]).example())


def test_sampled_from_samples():
    x = strategy(s.sampled_from((1, 2, 3)))
    assert x.example() in (1, 2, 3)


def test_none_is_none():
    assert strategy(None).example() is None


@pytest.mark.parametrize(
    u'col', [
        [], set(), frozenset(), {},
    ]
)
def test_sets_give_sets(col):
    x = strategy(col).example()
    assert x == col
    assert type(x) == type(col)


@pytest.mark.parametrize(
    u'coltype', [
        list, set, tuple, frozenset,
    ]
)
def test_single_boolean(coltype):
    x = find(
        coltype((bool,)), lambda x: len(x) >= 1
    )
    assert x == coltype((False,))


def test_frozensets_give_frozensets():
    assert isinstance(strategy(frozenset()).example(), frozenset)


def test_streaming():
    assert isinstance(strategy(s.streaming(bool)).example()[100], bool)


def test_random():
    strategy(Random).example().random()


def test_variadic_dictionaries():
    x = strategy(s.dictionary(bool, bool)).example()
    assert all(
        isinstance(k, bool) and isinstance(v, bool) for k, v in x.items())


def test_one_of():
    assert isinstance(strategy(s.one_of((bool, ()))).example(), (bool, tuple))


def test_fixed_dict():
    assert strategy({u'k': None}).example() == {u'k': None}


def test_sampled_from_one():
    assert strategy(s.sampled_from((1,))).example() == 1


def test_basic():
    assert isinstance(strategy(Bitfields).example(), integer_types)
    assert isinstance(strategy(Bitfields()).example(), integer_types)


def test_tree():
    tree = strategy(NAryTree(bool, bool, bool)).example()
    assert isinstance(tree, (Branch, Leaf))


@pytest.mark.parametrize(u'r', [
    s.floats_in_range(0, 1),
    s.floats_in_range(1, 2),
    s.floats_in_range(1, 1),
    s.floats_in_range(-sys.float_info.max, sys.float_info.max),
])
def test_float_ranges(r):
    assert r.start <= strategy(r).example() <= r.end


def test_strings():
    x = strategy(s.strings(u'a')).example()
    assert set(x).issubset(set(u'a'))


def test_empty_strings():
    assert strategy(s.strings(u'')).example() == u''


def test_single_float_in_range():
    assert strategy(s.floats_in_range(1, 1)).example() == 1


def test_float_range_validates():
    with pytest.raises(InvalidArgument):
        s.floats_in_range(2, 1)

    with pytest.raises(InvalidArgument):
        s.floats_in_range(1, float(u'inf'))


def test_sampled_from_validates():
    with pytest.raises(InvalidArgument):
        strategy(s.sampled_from([])).example()


def test_can_generate_named_tuples():
    T = namedtuple(u'T', (u'a', u'b'))
    t = find(T(int, int), lambda x: x.a < x.b)
    assert t.b == t.a + 1


def test_integers_from():
    assert find(s.integers_from(10), lambda x: True) == 10


def test_integers_range():
    assert find(s.integers_in_range(10, 100), lambda x: x > 10) == 11


def test_can_flatmap_non_strategies():
    x = strategy(int).flatmap(lambda x: bool)
    assert isinstance(x.example(), bool)


def test_can_define_settings():
    test_description = u'This is a setting just for these tests'
    assert not Settings.default.strict

    x = Settings()
    assert not x.strict

    Settings.define_setting(
        u'a_setting_just_for_these_tests',
        default=3,
        description=test_description,
    )

    assert test_description in Settings.a_setting_just_for_these_tests.__doc__

    assert x.a_setting_just_for_these_tests == 3
    assert Settings().a_setting_just_for_these_tests == 3


def test_cannot_define_a_setting_with_default_not_valid():
    with pytest.raises(InvalidArgument):
        Settings.define_setting(
            u'kittens',
            default=8, description=u'Kittens are pretty great',
            options=(1, 2, 3, 4),
        )


def test_define_setting_then_loading_profile():
    x = Settings()
    Settings.define_setting(
        u'fun_times',
        default=3, description=u'Something something spoon',
        options=(1, 2, 3, 4),
    )
    Settings.register_profile('hi', Settings(fun_times=2))
    assert x.fun_times == 3
    assert Settings.get_profile('hi').fun_times == 2


def test_picks_up_changes_to_defaults():
    Settings.default.max_examples = 18
    assert Settings.default.max_examples == 18
    s = Settings()
    assert s.max_examples == 18


def test_picks_up_changes_to_defaults_when_switching_profiles():
    original_default = Settings.default.max_examples
    Settings.load_profile('nonstrict')
    Settings.register_profile('test_settings', Settings())
    Settings.load_profile('test_settings')

    Settings.register_profile('other_test_settings', Settings())
    Settings.default.max_examples = 18
    assert Settings.default.max_examples == 18
    Settings.load_profile('other_test_settings')
    assert Settings.default.max_examples == original_default
    Settings.load_profile('test_settings')
    assert Settings.default.max_examples == 18


def test_does_not_pick_up_changes_after_instantiation():
    s = Settings()
    orig = s.max_examples
    Settings.default.max_examples = 18
    assert s.max_examples == orig


def test_can_assign_default_settings():
    Settings.default = Settings(max_examples=1100)
    assert Settings.default.max_examples == 1100
    with Settings(max_examples=10):
        assert Settings.default.max_examples == 10
    assert Settings.default.max_examples == 1100
