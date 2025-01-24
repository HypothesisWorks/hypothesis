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
from hypothesis.internal.conjecture.choice import choice_equal
from hypothesis.internal.floats import (
    count_between_floats,
    float_permitted,
    make_float_clamper,
    next_down,
    next_up,
    sign_aware_lte,
)

from tests.conjecture.common import float_kw, float_kwargs


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


# exponent comparisons:
@example(float_kw(1, float_info.max), 0)
@example(float_kw(1, float_info.max), 1)
@example(float_kw(1, float_info.max), 10)
@example(float_kw(1, float_info.max), float_info.max)
@example(float_kw(1, float_info.max), math.inf)
# mantissa comparisons:
@example(float_kw(100.0001, 100.0003), 100.0001)
@example(float_kw(100.0001, 100.0003), 100.0002)
@example(float_kw(100.0001, 100.0003), 100.0003)
@example(float_kw(100.0001, 100.0003, allow_nan=False), math.nan)
@example(float_kw(0, 10, allow_nan=False), math.nan)
@example(float_kw(0, 10, allow_nan=True), math.nan)
# the branch coverage of resampling in the "out of range of smallest magnitude" case
# relies on randomness from the mantissa. try a few different values.
@example(float_kw(-4, -1, smallest_nonzero_magnitude=4), 4)
@example(float_kw(-4, -1, smallest_nonzero_magnitude=4), 5)
@example(float_kw(-4, -1, smallest_nonzero_magnitude=4), 6)
@example(float_kw(1, 4, smallest_nonzero_magnitude=4), -4)
@example(float_kw(1, 4, smallest_nonzero_magnitude=4), -5)
@example(float_kw(1, 4, smallest_nonzero_magnitude=4), -6)
@example(float_kw(-5e-324, -0.0), 3.0)
@example(float_kw(0.0, 0.0), -0.0)
@example(float_kw(-0.0, -0.0), 0.0)
@given(float_kwargs(), st.floats())
def test_float_clamper(kwargs, input_value):
    min_value = kwargs["min_value"]
    max_value = kwargs["max_value"]
    allow_nan = kwargs["allow_nan"]
    smallest_nonzero_magnitude = kwargs["smallest_nonzero_magnitude"]
    clamper = make_float_clamper(
        min_value,
        max_value,
        smallest_nonzero_magnitude=smallest_nonzero_magnitude,
        allow_nan=allow_nan,
    )
    clamped = clamper(input_value)
    if math.isnan(clamped):
        # we should only clamp to nan if nans are allowed.
        assert allow_nan
    else:
        # otherwise, we should have clamped to something in the permitted range.
        assert sign_aware_lte(min_value, clamped)
        assert sign_aware_lte(clamped, max_value)

    # if input_value was permitted in the first place, then the clamped value should
    # be the same as the input value.
    if float_permitted(
        input_value,
        min_value=min_value,
        max_value=max_value,
        allow_nan=allow_nan,
        smallest_nonzero_magnitude=smallest_nonzero_magnitude,
    ):
        assert choice_equal(input_value, clamped)
