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
import math
from random import Random

import pytest

from hypothesis import find, given, assume
from hypothesis.strategies import lists, floats, integers, complex_numbers
from hypothesis.searchstrategy.numbers import is_integral, \
    FixedBoundedFloatStrategy
from hypothesis.searchstrategy.strategies import BadData


def test_minimize_negative_int():
    assert find(integers(), lambda x: x < 0) == -1
    assert find(integers(), lambda x: x < -1) == -2


def test_positive_negative_int():
    assert find(integers(), lambda x: x > 0) == 1
    assert find(integers(), lambda x: x > 1) == 2


boundaries = pytest.mark.parametrize(u'boundary', [0, 1, 11, 23, 64, 10000])


@boundaries
def test_minimizes_int_down_to_boundary(boundary):
    assert find(integers(), lambda x: x >= boundary) == boundary


@boundaries
def test_minimizes_int_up_to_boundary(boundary):
    assert find(integers(), lambda x: x <= -boundary) == -boundary


@boundaries
def test_minimizes_ints_from_down_to_boundary(boundary):
    assert find(
        integers(min_value=boundary - 10), lambda x: x >= boundary) == boundary

    assert find(integers(min_value=boundary), lambda x: True) == boundary


@boundaries
def test_minimizes_integer_range_to_boundary(boundary):
    assert find(
        integers(boundary, boundary + 100), lambda x: True
    ) == boundary


def test_single_integer_range_is_range():
    assert find(integers(1, 1), lambda x: True) == 1


def test_find_small_number_in_large_range():
    assert find(
        integers((-2 ** 32), 2 ** 32), lambda x: x >= 101) == 101


def test_find_small_sum_float_list():
    xs = find(
        lists(floats()),
        lambda x: len(x) >= 10 and sum(x) >= 1.0
    )
    assert sum(xs) <= 2.0


def test_finds_boundary_floats():
    def f(x):
        print(x)
        return True
    assert -1 <= find(floats(min_value=-1, max_value=1), f) <= 1


def test_find_non_boundary_float():
    x = find(floats(min_value=1, max_value=9), lambda x: x > 2)
    assert 2 < x < 3


def test_can_find_standard_complex_numbers():
    find(complex_numbers(), lambda x: x.imag != 0) == 0j
    find(complex_numbers(), lambda x: x.real != 0) == 1


def test_minimal_float_is_zero():
    assert find(floats(), lambda x: True) == 0.0


def test_negative_floats_simplify_to_zero():
    assert find(floats(), lambda x: x <= -1.0) == -1.0


def test_find_infinite_float_is_positive():
    assert find(floats(), math.isinf) == float(u'inf')


def test_can_find_infinite_negative_float():
    assert find(floats(), lambda x: x < -sys.float_info.max)


def test_can_find_float_on_boundary_of_representable():
    find(floats(), lambda x: x + 1 == x and not math.isinf(x))


def test_minimize_nan():
    assert math.isnan(find(floats(), math.isnan))


def test_minimize_very_large_float():
    t = sys.float_info.max / 2
    assert t <= find(floats(), lambda x: x >= t) < float(u'inf')


def test_can_find_float_far_from_integral():
    find(floats(), lambda x: not (
        math.isnan(x) or
        math.isinf(x) or
        is_integral(x * (2 ** 32))
    ))


def test_can_find_integrish():
    find(floats(), lambda x: (
        is_integral(x * (2 ** 32)) and not is_integral(x * 16)
    ))


def test_list_of_fractional_float():
    assert set(find(
        lists(floats()), lambda x: len([t for t in x if t >= 1.5]) >= 10
    )) in (
        set((1.5,)),
        set((1.5, 2.0)),
        set((2.0,)),
    )


def test_minimal_fractional_float():
    assert find(floats(), lambda x: x >= 1.5) in (1.5, 2.0)


def test_minimizes_lists_of_negative_ints_up_to_boundary():
    result = find(
        lists(integers()), lambda x: len([t for t in x if t <= -1]) >= 10)
    assert result == [-1] * 10


def test_out_of_range_integers_are_bad():
    with pytest.raises(BadData):
        integers(0, 1).from_basic(-1)

    with pytest.raises(BadData):
        integers(min_value=11).from_basic(9)


def test_out_of_range_floats_are_bad():
    with pytest.raises(BadData):
        floats(11, 12).from_basic(floats(0, 1).to_basic((0, 0.0)))

    with pytest.raises(BadData):
        FixedBoundedFloatStrategy(11, 12).from_basic(
            floats().to_basic(float(u'nan'))
        )


def test_float_simplicity():
    s = floats().strictly_simpler

    def order(x, y):
        x = float(x)
        y = float(y)
        assert s(x, y)
        assert not s(y, x)

    order(sys.float_info.max, u'-inf')
    order(1.0, 0.5)
    order(1.0, 2.0)
    order(2, -1)
    order(-1.5, float(u'inf'))
    order(-1.2, -1.3)
    order(u'inf', u'nan')
    order(u'inf', u'-inf')
    order(u'0.25', u'0.5')
    order(0.5, -1)
    order(1.5, u'-inf')


def test_floats_can_simplify_extreme_values():
    s = floats()
    r = Random(1)
    for simplify in s.simplifiers(r, 3.14159):
        for v in (float(u'nan'), float(u'inf'), float(u'-inf')):
            list(simplify(r, v))


@pytest.mark.parametrize((u'left', u'right'), [
    (0.0, 5e-324),
    (-5e-324, 0.0),
    (-5e-324, 5e-324),
    (5e-324, 1e-323),
])
def test_floats_in_constrained_range(left, right):
    @given(floats(left, right))
    def test_in_range(r):
        assert left <= r <= right
    test_in_range()


def test_floats_of_small_range_are_bounded():
    assert floats(0, 5e-324).template_upper_bound == 2
    assert floats(-5e-324, 5e-324).template_upper_bound == 4


@given(floats(), floats())
def test_bounds_are_valid(left, right):
    for x in (left, right):
        assume(not (math.isinf(x) or math.isnan(x)))
    assume(left <= right)
    ub = floats(left, right).template_upper_bound
    assert ub >= 0
    if isinstance(ub, float):
        assert math.isinf(ub)
    else:
        assert isinstance(ub, int)


def test_bounds_are_respected():
    assert find(floats(min_value=1.0), lambda x: True) == 1.0
    assert find(floats(max_value=-1.0), lambda x: True) == -1.0


@pytest.mark.parametrize(
    'k', range(10)
)
def test_floats_from_zero_have_reasonable_range(k):
    n = 10 ** k
    assert find(floats(min_value=0.0), lambda x: x >= n) == float(n)
    assert find(floats(max_value=0.0), lambda x: x <= -n) == float(-n)


def test_explicit_allow_nan():
    find(floats(allow_nan=True), math.isnan)


def test_one_sided_contains_infinity():
    find(floats(min_value=1.0), math.isinf)
    find(floats(max_value=1.0), math.isinf)


@given(floats(min_value=0.0, allow_infinity=False))
def test_no_allow_infinity_upper(x):
    assert not math.isinf(x)


@given(floats(max_value=0.0, allow_infinity=False))
def test_no_allow_infinity_lower(x):
    assert not math.isinf(x)


class TestFloatsAreFloats(object):

    @given(floats())
    def test_unbounded(self, arg):
        assert isinstance(arg, float)

    @given(floats(min_value=0, max_value=2 ** 64 - 1))
    def test_int_int(self, arg):
        assert isinstance(arg, float)

    @given(floats(min_value=0, max_value=float(2 ** 64 - 1)))
    def test_int_float(self, arg):
        assert isinstance(arg, float)

    @given(floats(min_value=float(0), max_value=2 ** 64 - 1))
    def test_float_int(self, arg):
        assert isinstance(arg, float)

    @given(floats(min_value=float(0), max_value=float(2 ** 64 - 1)))
    def test_float_float(self, arg):
        assert isinstance(arg, float)
