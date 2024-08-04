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
import sys
import warnings

import pytest

from hypothesis import assume, given, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.internal.floats import (
    float_of,
    float_to_int,
    int_to_float,
    is_negative,
    next_down,
    next_up,
)

from tests.common.debug import find_any, minimal

try:
    import numpy
except ImportError:
    numpy = None


@pytest.mark.parametrize(
    ("lower", "upper"),
    [
        # Exact values don't matter, but they're large enough so that x + y = inf.
        (9.9792015476736e291, 1.7976931348623157e308),
        (-sys.float_info.max, sys.float_info.max),
    ],
)
@given(data=st.data())
def test_floats_are_in_range(data, lower, upper):
    t = data.draw(st.floats(lower, upper))
    assert lower <= t <= upper


@pytest.mark.parametrize("sign", [-1, 1])
def test_can_generate_both_zeros(sign):
    assert minimal(st.floats(), lambda x: math.copysign(1, x) == sign) == sign * 0.0


@pytest.mark.parametrize(
    ("l", "r"),
    [(-1.0, 1.0), (-0.0, 1.0), (-1.0, 0.0), (-sys.float_info.min, sys.float_info.min)],
)
@pytest.mark.parametrize("sign", [-1, 1])
def test_can_generate_both_zeros_when_in_interval(l, r, sign):
    assert minimal(st.floats(l, r), lambda x: math.copysign(1, x) == sign) == sign * 0.0


@given(st.floats(0.0, 1.0))
def test_does_not_generate_negative_if_right_boundary_is_positive(x):
    assert math.copysign(1, x) == 1


@given(st.floats(-1.0, -0.0))
def test_does_not_generate_positive_if_right_boundary_is_negative(x):
    assert math.copysign(1, x) == -1


def test_half_bounded_generates_zero():
    find_any(st.floats(min_value=-1.0), lambda x: x == 0.0)
    find_any(st.floats(max_value=1.0), lambda x: x == 0.0)


@given(st.floats(max_value=-0.0))
def test_half_bounded_respects_sign_of_upper_bound(x):
    assert math.copysign(1, x) == -1


@given(st.floats(min_value=0.0))
def test_half_bounded_respects_sign_of_lower_bound(x):
    assert math.copysign(1, x) == 1


@given(st.floats(allow_nan=False))
def test_filter_nan(x):
    assert not math.isnan(x)


@given(st.floats(allow_infinity=False))
def test_filter_infinity(x):
    assert not math.isinf(x)


def test_can_guard_against_draws_of_nan():
    """In this test we create a NaN value that naturally "tries" to shrink into
    the first strategy, where it is not permitted. This tests a case that is
    very unlikely to happen in random generation: When the unconstrained first
    branch of generating a float just happens to produce a NaN value.

    Here what happens is that we get a NaN from the *second* strategy,
    but this then shrinks into its unconstrained branch. The natural
    thing to happen is then to try to zero the branch parameter of the
    one_of, but that will put an illegal value there, so it's not
    allowed to happen.
    """
    tagged_floats = st.one_of(
        st.tuples(st.just(0), st.floats(allow_nan=False)),
        st.tuples(st.just(1), st.floats(allow_nan=True)),
    )

    tag, f = minimal(tagged_floats, lambda x: math.isnan(x[1]))
    assert tag == 1


def test_very_narrow_interval():
    upper_bound = -1.0
    lower_bound = int_to_float(float_to_int(upper_bound) + 10)
    assert lower_bound < upper_bound

    @given(st.floats(lower_bound, upper_bound))
    def test(f):
        assert lower_bound <= f <= upper_bound

    test()


@given(st.floats())
def test_up_means_greater(x):
    hi = next_up(x)
    if not x < hi:
        assert (
            (math.isnan(x) and math.isnan(hi))
            or (x > 0 and math.isinf(x))
            or (x == hi == 0 and is_negative(x) and not is_negative(hi))
        )


@given(st.floats())
def test_down_means_lesser(x):
    lo = next_down(x)
    if not x > lo:
        assert (
            (math.isnan(x) and math.isnan(lo))
            or (x < 0 and math.isinf(x))
            or (x == lo == 0 and is_negative(lo) and not is_negative(x))
        )


@given(st.floats(allow_nan=False, allow_infinity=False))
def test_updown_roundtrip(val):
    assert val == next_up(next_down(val))
    assert val == next_down(next_up(val))


@given(st.floats(width=32, allow_infinity=False))
def test_float32_can_exclude_infinity(x):
    assert not math.isinf(x)


@given(st.floats(width=16, allow_infinity=False))
def test_float16_can_exclude_infinity(x):
    assert not math.isinf(x)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_value": 10**5, "width": 16},
        {"max_value": 10**5, "width": 16},
        {"min_value": 10**40, "width": 32},
        {"max_value": 10**40, "width": 32},
        {"min_value": 10**400, "width": 64},
        {"max_value": 10**400, "width": 64},
        {"min_value": 10**400},
        {"max_value": 10**400},
    ],
)
def test_out_of_range(kwargs):
    with pytest.raises(OverflowError):
        st.floats(**kwargs).validate()


def test_disallowed_width():
    with pytest.raises(InvalidArgument):
        st.floats(width=128).validate()


def test_no_single_floats_in_range():
    low = 2.0**25 + 1
    high = low + 2
    st.floats(low, high).validate()  # Note: OK for 64bit floats
    with warnings.catch_warnings():
        # Unrepresentable bounds are deprecated, but we're not testing that here
        warnings.simplefilter("ignore")
        with pytest.raises(InvalidArgument):
            st.floats(low, high, width=32).validate()


# If the floats() strategy adds random floats to a value as large as 10^304
# without handling overflow, we are very likely to generate infinity.
@given(st.floats(min_value=1e304, allow_infinity=False))
def test_finite_min_bound_does_not_overflow(x):
    assert not math.isinf(x)


@given(st.floats(max_value=-1e304, allow_infinity=False))
def test_finite_max_bound_does_not_overflow(x):
    assert not math.isinf(x)


@given(st.floats(0, 1, exclude_min=True, exclude_max=True))
def test_can_exclude_endpoints(x):
    assert 0 < x < 1


@given(st.floats(-math.inf, -1e307, exclude_min=True))
def test_can_exclude_neg_infinite_endpoint(x):
    assert not math.isinf(x)


@given(st.floats(1e307, math.inf, exclude_max=True))
def test_can_exclude_pos_infinite_endpoint(x):
    assert not math.isinf(x)


def test_exclude_infinite_endpoint_is_invalid():
    with pytest.raises(InvalidArgument):
        st.floats(min_value=math.inf, exclude_min=True).validate()
    with pytest.raises(InvalidArgument):
        st.floats(max_value=-math.inf, exclude_max=True).validate()


@pytest.mark.parametrize("lo,hi", [(True, False), (False, True), (True, True)])
@given(bound=st.floats(allow_nan=False, allow_infinity=False).filter(bool))
def test_exclude_entire_interval(lo, hi, bound):
    with pytest.raises(InvalidArgument, match="exclude_min=.+ and exclude_max="):
        st.floats(bound, bound, exclude_min=lo, exclude_max=hi).validate()


def test_zero_intervals_are_OK():
    st.floats(0.0, 0.0).validate()
    st.floats(-0.0, 0.0).validate()
    st.floats(-0.0, -0.0).validate()


@pytest.mark.parametrize("lo", [0.0, -0.0])
@pytest.mark.parametrize("hi", [0.0, -0.0])
@pytest.mark.parametrize("exmin,exmax", [(True, False), (False, True), (True, True)])
def test_cannot_exclude_endpoint_with_zero_interval(lo, hi, exmin, exmax):
    with pytest.raises(InvalidArgument):
        st.floats(lo, hi, exclude_min=exmin, exclude_max=exmax).validate()


WIDTHS = (64, 32, 16)


@pytest.mark.parametrize("nonfloat", [st.nothing(), st.none()])
@given(data=st.data(), width=st.sampled_from(WIDTHS))
def test_fuzzing_floats_bounds(data, width, nonfloat):
    lo = data.draw(nonfloat | st.floats(allow_nan=False, width=width), label="lo")
    hi = data.draw(nonfloat | st.floats(allow_nan=False, width=width), label="hi")
    if lo is not None and hi is not None and lo > hi:
        lo, hi = hi, lo
    assume(lo != 0 or hi != 0)
    value = data.draw(
        st.floats(min_value=lo, max_value=hi, width=width, allow_nan=False),
        label="value",
    )
    assert value == float_of(value, width=width)
    assert lo is None or lo <= value
    assert hi is None or value <= hi
