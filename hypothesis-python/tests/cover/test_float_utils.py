# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math
from sys import float_info

import pytest

from hypothesis import example, given, strategies as st
from hypothesis.internal.floats import (
    count_between_floats,
    float_to_int,
    make_float_clamper,
    next_down,
    next_up,
    sign_aware_lte,
    sign_aware_max,
    sign_aware_min,
)


def test_can_handle_straddling_zero():
    assert count_between_floats(-0.0, 0.0) == 2


@pytest.mark.parametrize(
    "func,val",
    [
        (next_up, math.nan),
        (next_up, math.inf),
        (next_up, -0.0),
        (next_down, math.nan),
        (next_down, -math.inf),
        (next_down, 0.0),
    ],
)
def test_next_float_equal(func, val):
    if math.isnan(val):
        assert math.isnan(func(val))
    else:
        assert func(val) == val


# invalid order -> clamper is None:
@example(2.0, 1.0, 3.0)
# exponent comparisons:
@example(1, float_info.max, 0)
@example(1, float_info.max, 1)
@example(1, float_info.max, 10)
@example(1, float_info.max, float_info.max)
@example(1, float_info.max, math.inf)
# mantissa comparisons:
@example(100.0001, 100.0003, 100.0001)
@example(100.0001, 100.0003, 100.0002)
@example(100.0001, 100.0003, 100.0003)
@given(st.floats(min_value=0), st.floats(min_value=0), st.floats(min_value=0))
def test_float_clamper(min_value, max_value, input_value):
    clamper = make_float_clamper(min_value, max_value, allow_zero=False)
    if max_value < min_value:
        assert clamper is None
        return
    clamped = clamper(input_value)
    if min_value <= input_value <= max_value:
        assert input_value == clamped
    else:
        assert min_value <= clamped <= max_value


@example(0.01, math.inf, 0.0)
@given(st.floats(min_value=0), st.floats(min_value=0), st.floats(min_value=0))
def test_float_clamper_with_allowed_zeros(min_value, max_value, input_value):
    clamper = make_float_clamper(min_value, max_value, allow_zero=True)
    assert clamper is not None
    clamped = clamper(input_value)
    if input_value == 0.0 or max_value < min_value:
        assert clamped == 0.0
    elif min_value <= input_value <= max_value:
        assert input_value == clamped
    else:
        assert min_value <= clamped <= max_value


@pytest.mark.parametrize(
    "x, y, expected",
    [
        (-1, 1, True),
        (1, -1, False),
        (0.0, 0.0, True),
        (-0.0, 0.0, True),
        (0.0, -0.0, False),
    ],
)
def test_sign_aware_lte(x, y, expected):
    assert sign_aware_lte(x, y) is expected


@pytest.mark.parametrize(
    "x, y, expected",
    [(-1, 1, 1), (1, -1, 1), (0.0, 0.0, 0.0), (-0.0, 0.0, 0.0), (0.0, -0.0, 0.0)],
)
def test_sign_aware_max(x, y, expected):
    assert float_to_int(sign_aware_max(x, y)) == float_to_int(expected)


@pytest.mark.parametrize(
    "x, y, expected",
    [(-1, 1, -1), (1, -1, -1), (0.0, 0.0, 0.0), (-0.0, 0.0, -0.0), (0.0, -0.0, -0.0)],
)
def test_sign_aware_min(x, y, expected):
    assert float_to_int(sign_aware_min(x, y)) == float_to_int(expected)
