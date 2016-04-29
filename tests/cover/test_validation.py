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

import pytest

from hypothesis import find, given, settings
from hypothesis.errors import InvalidArgument
from tests.common.utils import fails_with
from hypothesis.strategies import sets, lists, floats, booleans, \
    integers, recursive, frozensets


def test_errors_when_given_varargs():
    @given(integers())
    def has_varargs(*args):
        pass
    with pytest.raises(InvalidArgument) as e:
        has_varargs()
    assert u'varargs' in e.value.args[0]


def test_varargs_without_positional_arguments_allowed():
    @given(somearg=integers())
    def has_varargs(somearg, *args):
        pass


def test_errors_when_given_varargs_and_kwargs_with_positional_arguments():
    @given(integers())
    def has_varargs(*args, **kw):
        pass
    with pytest.raises(InvalidArgument) as e:
        has_varargs()
    assert u'varargs' in e.value.args[0]


def test_varargs_and_kwargs_without_positional_arguments_allowed():
    @given(somearg=integers())
    def has_varargs(*args, **kw):
        pass


def test_bare_given_errors():
    @given()
    def test():
        pass

    with pytest.raises(InvalidArgument):
        test()


def test_errors_on_unwanted_kwargs():
    @given(hello=int, world=int)
    def greet(world):
        pass
    with pytest.raises(InvalidArgument):
        greet()


def test_errors_on_too_many_positional_args():
    @given(integers(), int, int)
    def foo(x, y):
        pass

    with pytest.raises(InvalidArgument):
        foo()


def test_errors_on_any_varargs():
    @given(integers())
    def oops(*args):
        pass
    with pytest.raises(InvalidArgument):
        oops()


def test_can_put_arguments_in_the_middle():
    @given(y=integers())
    def foo(x, y, z):
        pass
    foo(1, 2)


def test_float_ranges():
    with pytest.raises(InvalidArgument):
        floats(float(u'nan'), 0).example()
    with pytest.raises(InvalidArgument):
        floats(1, -1).example()


def test_float_range_and_allow_nan_cannot_both_be_enabled():
    with pytest.raises(InvalidArgument):
        floats(min_value=1, allow_nan=True).example()
    with pytest.raises(InvalidArgument):
        floats(max_value=1, allow_nan=True).example()


def test_float_finite_range_and_allow_infinity_cannot_both_be_enabled():
    with pytest.raises(InvalidArgument):
        floats(0, 1, allow_infinity=True).example()


def test_does_not_error_if_min_size_is_bigger_than_default_size():
    lists(integers(), min_size=50).example()
    sets(integers(), min_size=50).example()
    frozensets(integers(), min_size=50).example()
    lists(integers(), min_size=50, unique=True).example()


def test_list_unique_and_unique_by_cannot_both_be_enabled():
    @given(lists(integers(), unique=True, unique_by=lambda x: x))
    def boom(t):
        pass
    with pytest.raises(InvalidArgument) as e:
        boom()
    assert 'unique ' in e.value.args[0]
    assert 'unique_by' in e.value.args[0]


def test_an_average_size_must_be_positive():
    with pytest.raises(InvalidArgument):
        lists(integers(), average_size=0.0).example()
    with pytest.raises(InvalidArgument):
        lists(integers(), average_size=-1.0).example()


def test_an_average_size_may_be_zero_if_max_size_is():
    lists(integers(), average_size=0.0, max_size=0)


def test_min_before_max():
    with pytest.raises(InvalidArgument):
        integers(min_value=1, max_value=0).validate()


def test_filter_validates():
    with pytest.raises(InvalidArgument):
        integers(min_value=1, max_value=0).filter(bool).validate()


def test_recursion_validates_base_case():
    with pytest.raises(InvalidArgument):
        recursive(
            integers(min_value=1, max_value=0),
            lists,
        ).validate()


def test_recursion_validates_recursive_step():
    with pytest.raises(InvalidArgument):
        recursive(
            integers(),
            lambda x: lists(x, min_size=3, max_size=1),
        ).validate()


@fails_with(InvalidArgument)
@given(x=integers())
def test_stuff_keyword(x=1):
    pass


@fails_with(InvalidArgument)
@given(integers())
def test_stuff_positional(x=1):
    pass


@fails_with(InvalidArgument)
@given(integers(), integers())
def test_too_many_positional(x):
    pass


def test_given_warns_on_use_of_non_strategies():
    @given(bool)
    @settings(strict=False)
    def test(x):
        pass
    with pytest.raises(InvalidArgument):
        test()


def test_given_warns_when_mixing_positional_with_keyword():
    @given(booleans(), y=booleans())
    @settings(strict=False)
    def test(x, y):
        pass
    with pytest.raises(InvalidArgument):
        test()


def test_cannot_find_non_strategies():
    with pytest.raises(InvalidArgument):
        find(bool, bool)
