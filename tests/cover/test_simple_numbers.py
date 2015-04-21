# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import sys
import math

import pytest
from hypothesis import find
from hypothesis.specifiers import integers_from, floats_in_range, \
    integers_in_range
from hypothesis.searchstrategy.numbers import is_integral


def test_minimize_negative_int():
    assert find(int, lambda x: x < 0) == -1
    assert find(int, lambda x: x < -1) == -2


def test_positive_negative_int():
    assert find(int, lambda x: x > 0) == 1
    assert find(int, lambda x: x > 1) == 2


boundaries = pytest.mark.parametrize('boundary', [0, 1, 11, 23, 64, 10000])


@boundaries
def test_minimizes_int_down_to_boundary(boundary):
    assert find(int, lambda x: x >= boundary) == boundary


@boundaries
def test_minimizes_int_up_to_boundary(boundary):
    assert find(int, lambda x: x <= -boundary) == -boundary


@boundaries
def test_minimizes_ints_from_down_to_boundary(boundary):
    assert find(
        integers_from(boundary - 10), lambda x: x >= boundary) == boundary

    assert find(integers_from(boundary), lambda x: True) == boundary


@boundaries
def test_minimizes_integer_range_to_boundary(boundary):
    assert find(
        integers_in_range(boundary, boundary + 100), lambda x: True
    ) == boundary


def test_single_integer_range_is_range():
    assert find(integers_in_range(1, 1), lambda x: True) == 1


def test_find_small_number_in_large_range():
    assert find(
        integers_in_range((-2 ** 32), 2 ** 32), lambda x: x >= 101) == 101


def test_find_small_sum_float_list():
    xs = find(
        [float],
        lambda x: len(x) >= 10 and sum(x) >= 1.0
    )
    assert sum(xs) <= 2.0


def test_finds_boundary_floats():
    assert find(floats_in_range(-1, 1), lambda x: True) == -1


def test_find_non_boundary_float():
    x = find(floats_in_range(1, 9), lambda x: x > 2)
    assert 2 < x < 3


def test_can_find_standard_complex_numbers():
    find(complex, lambda x: x.imag != 0) == 0j
    find(complex, lambda x: x.real != 0) == 1


def test_minimial_float_is_zero():
    assert find(float, lambda x: True) == 0.0


def test_negative_floats_simplify_to_zero():
    assert find(float, lambda x: x <= -1.0) == -1.0


def test_find_infinite_float_is_positive():
    assert find(float, math.isinf) == float('inf')


def test_can_find_infinite_negative_float():
    assert find(float, lambda x: x < -sys.float_info.max)


def test_can_find_float_on_boundary_of_representable():
    find(float, lambda x: x + 1 == x and not math.isinf(x))


def test_minimize_nan():
    assert math.isnan(find(float, math.isnan))


def test_minimize_very_large_float():
    t = sys.float_info.max / 2
    assert t <= find(float, lambda x: x >= t) < float('inf')


def test_can_find_float_far_from_integral():
    find(float, lambda x: not (
        math.isnan(x) or
        math.isinf(x) or
        is_integral(x * (2 ** 32))
    ))


def test_list_of_fractional_float():
    assert set(find(
        [float], lambda x: len([t for t in x if t >= 1.5]) >= 10
    )) in (
        {1.5},
        {1.5, 2.0}
    )


def test_minimal_fractional_float():
    assert find(float, lambda x: x >= 1.5) in (1.5, 2.0)
