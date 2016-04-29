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

import math

import pytest

import hypothesis.strategies as ds
from hypothesis import find, given, settings
from hypothesis.errors import InvalidArgument
from hypothesis.internal.reflection import nicerepr


def fn_test(*fnkwargs):
    fnkwargs = list(fnkwargs)
    return pytest.mark.parametrize(
        (u'fn', u'args'), fnkwargs,
        ids=[
            u'%s(%s)' % (fn.__name__, u', '.join(map(nicerepr, args)))
            for fn, args in fnkwargs
        ]
    )


def fn_ktest(*fnkwargs):
    fnkwargs = list(fnkwargs)
    return pytest.mark.parametrize(
        (u'fn', u'kwargs'), fnkwargs,
        ids=[
            u'%s(%s)' % (fn.__name__, u', '.join(sorted(
                u'%s=%r' % (k, v)
                for k, v in kwargs.items()
            )),)
            for fn, kwargs in fnkwargs
        ]
    )


@fn_ktest(
    (ds.integers, {u'min_value': float(u'nan')}),
    (ds.integers, {u'min_value': 2, u'max_value': 1}),
    (ds.lists, {}),
    (ds.lists, {u'average_size': float(u'nan')}),
    (ds.lists, {u'min_size': 10, u'max_size': 9}),
    (ds.lists, {u'min_size': -10, u'max_size': -9}),
    (ds.lists, {u'max_size': -9}),
    (ds.lists, {u'max_size': 10}),
    (ds.lists, {u'min_size': -10}),
    (ds.lists, {u'max_size': 10, u'average_size': 20}),
    (ds.lists, {u'min_size': 1.0, u'average_size': 0.5}),
    (ds.lists, {u'elements': u'hi'}),
    (ds.text, {u'min_size': 10, u'max_size': 9}),
    (ds.text, {u'max_size': 10, u'average_size': 20}),
    (ds.binary, {u'min_size': 10, u'max_size': 9}),
    (ds.binary, {u'max_size': 10, u'average_size': 20}),
    (ds.floats, {u'min_value': float(u'nan')}),
    (ds.floats, {u'max_value': 0.0, u'min_value': 1.0}),
    (ds.fixed_dictionaries, {u'mapping': u'fish'}),
    (ds.fixed_dictionaries, {u'mapping': {1: u'fish'}}),
    (ds.dictionaries, {u'keys': ds.integers(), u'values': 1}),
    (ds.dictionaries, {u'keys': 1, u'values': ds.integers()}),
    (ds.text, {u'alphabet': u'', u'min_size': 1}),
)
def test_validates_keyword_arguments(fn, kwargs):
    with pytest.raises(InvalidArgument):
        fn(**kwargs).example()


@fn_ktest(
    (ds.integers, {u'min_value': 0}),
    (ds.integers, {u'min_value': 11}),
    (ds.integers, {u'min_value': 11, u'max_value': 100}),
    (ds.integers, {u'max_value': 0}),
    (ds.lists, {u'max_size': 0}),
    (ds.lists, {u'elements': ds.integers()}),
    (ds.lists, {u'elements': ds.integers(), u'max_size': 5}),
    (ds.lists, {u'elements': ds.booleans(), u'min_size': 5}),
    (ds.lists, {u'elements': ds.booleans(), u'min_size': 5, u'max_size': 10}),
    (ds.lists, {
        u'average_size': 20, u'elements': ds.booleans(), u'max_size': 25}),
    (ds.sets, {
        u'min_size': 10, u'max_size': 10, u'elements': ds.integers(),
    }),
    (ds.booleans, {}),
    (ds.just, {u'value': u'hi'}),
    (ds.integers, {u'min_value': 12, u'max_value': 12}),
    (ds.floats, {}),
    (ds.floats, {u'min_value': 1.0}),
    (ds.floats, {u'max_value': 1.0}),
    (ds.floats, {u'max_value': 1.0, u'min_value': -1.0}),
    (ds.sampled_from, {u'elements': [1]}),
    (ds.sampled_from, {u'elements': [1, 2, 3]}),
    (ds.fixed_dictionaries, {u'mapping': {1: ds.integers()}}),
    (ds.dictionaries, {u'keys': ds.booleans(), u'values': ds.integers()}),
    (ds.text, {u'alphabet': u'abc'}),
    (ds.text, {u'alphabet': u''}),
    (ds.text, {u'alphabet': ds.sampled_from(u'abc')}),
)
def test_produces_valid_examples_from_keyword(fn, kwargs):
    fn(**kwargs).example()


@fn_test(
    (ds.one_of, (1,))
)
def test_validates_args(fn, args):
    with pytest.raises(InvalidArgument):
        fn(*args).example()


@fn_test(
    (ds.one_of, (ds.booleans(), ds.tuples(ds.booleans()))),
    (ds.one_of, (ds.booleans(),)),
    (ds.text, ()),
    (ds.binary, ()),
    (ds.builds, (lambda x, y: x + y, ds.integers(), ds.integers())),
)
def test_produces_valid_examples_from_args(fn, args):
    fn(*args).example()


def test_tuples_raise_error_on_bad_kwargs():
    with pytest.raises(TypeError):
        ds.tuples(stuff=u'things')


@given(ds.lists(ds.booleans(), min_size=10, max_size=10))
def test_has_specified_length(xs):
    assert len(xs) == 10


@given(ds.integers(max_value=100))
@settings(max_examples=100)
def test_has_upper_bound(x):
    assert x <= 100


@given(ds.integers(min_value=100))
def test_has_lower_bound(x):
    assert x >= 100


@given(ds.integers(min_value=1, max_value=2))
def test_is_in_bounds(x):
    assert 1 <= x <= 2


def test_float_can_find_max_value_inf():
    assert find(
        ds.floats(max_value=float(u'inf')), lambda x: math.isinf(x)
    ) == float(u'inf')
    assert find(
        ds.floats(min_value=0.0), lambda x: math.isinf(x)) == float(u'inf')


def test_float_can_find_min_value_inf():
    find(ds.floats(), lambda x: x < 0 and math.isinf(x))
    find(
        ds.floats(min_value=float(u'-inf'), max_value=0.0),
        lambda x: math.isinf(x))


def test_can_find_none_list():
    assert find(ds.lists(ds.none()), lambda x: len(x) >= 3) == [None] * 3


def test_fractions():
    assert find(ds.fractions(), lambda f: f >= 1) == 1


def test_decimals():
    assert find(ds.decimals(), lambda f: f.is_finite() and f >= 1) == 1


def test_non_float_decimal():
    find(ds.decimals(), lambda d: ds.float_to_decimal(float(d)) != d)


def test_produces_dictionaries_of_at_least_minimum_size():
    t = find(
        ds.dictionaries(ds.booleans(), ds.integers(), min_size=2),
        lambda x: True)
    assert t == {False: 0, True: 0}


@given(ds.dictionaries(ds.integers(), ds.integers(), max_size=5))
@settings(max_examples=50)
def test_dictionaries_respect_size(d):
    assert len(d) <= 5


@given(ds.dictionaries(ds.integers(), ds.integers(), max_size=0))
@settings(max_examples=50)
def test_dictionaries_respect_zero_size(d):
    assert len(d) <= 5


@given(
    ds.lists(ds.none(), max_size=5)
)
def test_none_lists_respect_max_size(ls):
    assert len(ls) <= 5


@given(
    ds.lists(ds.none(), max_size=5, min_size=1)
)
def test_none_lists_respect_max_and_min_size(ls):
    assert 1 <= len(ls) <= 5
