# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

import sys
import math
import warnings
from decimal import Decimal

import pytest
from flaky import flaky

import hypothesis.strategies as st
from hypothesis import given, assume, settings
from hypothesis.errors import InvalidArgument
from tests.common.debug import minimal, find_any
from tests.common.utils import checks_deprecated_behaviour
from hypothesis.internal.compat import WINDOWS, CAN_PACK_HALF_FLOAT
from hypothesis.internal.floats import next_up, next_down, float_to_int, \
    int_to_float

try:
    import numpy
except ImportError:
    numpy = None


@pytest.mark.parametrize(('lower', 'upper'), [
    # Exact values don't matter, but they're large enough so that x + y = inf.
    (9.9792015476736e+291, 1.7976931348623157e+308),
    (-sys.float_info.max, sys.float_info.max)
])
def test_floats_are_in_range(lower, upper):
    @given(st.floats(lower, upper))
    def test_is_in_range(t):
        assert lower <= t <= upper
    test_is_in_range()


@pytest.mark.parametrize('sign', [-1, 1])
def test_can_generate_both_zeros(sign):
    assert minimal(
        st.floats(),
        lambda x: math.copysign(1, x) == sign,
    ) == sign * 0.0


@pytest.mark.parametrize((u'l', u'r'), [
    (-1.0, 1.0),
    (-0.0, 1.0),
    (-1.0, 0.0),
    (-sys.float_info.min, sys.float_info.min),
])
@pytest.mark.parametrize('sign', [-1, 1])
def test_can_generate_both_zeros_when_in_interval(l, r, sign):
    assert minimal(
        st.floats(l, r),
        lambda x: math.copysign(1, x) == sign) == sign * 0.0


@given(st.floats(0.0, 1.0))
def test_does_not_generate_negative_if_right_boundary_is_positive(x):
    assert math.copysign(1, x) == 1


@given(st.floats(-1.0, -0.0))
def test_does_not_generate_positive_if_right_boundary_is_negative(x):
    assert math.copysign(1, x) == -1


@pytest.mark.parametrize((u'l', u'r'), [
    (0.0, 1.0),
    (-1.0, 0.0),
    (-sys.float_info.min, sys.float_info.min),
])
@flaky(max_runs=4, min_passes=1)
def test_can_generate_interval_endpoints(l, r):
    interval = st.floats(l, r)
    minimal(interval, lambda x: x == l, settings=settings(max_examples=10000))
    minimal(interval, lambda x: x == r, settings=settings(max_examples=10000))


@flaky(max_runs=4, min_passes=1)
def test_half_bounded_generates_endpoint():
    find_any(st.floats(min_value=-1.0), lambda x: x == -1.0)
    find_any(st.floats(max_value=-1.0), lambda x: x == -1.0)


def test_half_bounded_generates_zero():
    find_any(st.floats(min_value=-1.0), lambda x: x == 0.0)
    find_any(st.floats(max_value=1.0), lambda x: x == 0.0)


@pytest.mark.xfail(
    WINDOWS,
    reason=(
        'Seems to be triggering a floating point bug on 2.7 + windows + x64'))
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
        assert (math.isnan(x) and math.isnan(hi)) or (x > 0 and math.isinf(x))


@given(st.floats())
def test_down_means_lesser(x):
    lo = next_down(x)
    if not x > lo:
        assert (math.isnan(x) and math.isnan(lo)) or (x < 0 and math.isinf(x))


@given(st.floats(allow_nan=False, allow_infinity=False))
def test_updown_roundtrip(val):
    assert val == next_up(next_down(val))
    assert val == next_down(next_up(val))


@checks_deprecated_behaviour
@given(st.data(), st.floats(allow_nan=False, allow_infinity=False))
def test_floats_in_tiny_interval_within_bounds(data, center):
    assume(not (math.isinf(next_down(center)) or math.isinf(next_up(center))))
    lo = Decimal.from_float(next_down(center)).next_plus()
    hi = Decimal.from_float(next_up(center)).next_minus()
    assert float(lo) < lo < center < hi < float(hi)
    val = data.draw(st.floats(lo, hi))
    assert lo < val < hi


@checks_deprecated_behaviour
def test_float_free_interval_is_invalid():
    lo = (2 ** 54) + 1
    hi = lo + 2
    assert float(lo) < lo < hi < float(hi), 'There are no floats in [lo .. hi]'
    with pytest.raises(InvalidArgument):
        st.floats(lo, hi).example()


@given(st.floats(width=32, allow_infinity=False))
def test_float32_can_exclude_infinity(x):
    assert not math.isinf(x)


@pytest.mark.skipif(not (numpy or CAN_PACK_HALF_FLOAT), reason='dependency')
@given(st.floats(width=32, allow_infinity=False))
def test_float16_can_exclude_infinity(x):
    assert not math.isinf(x)


@pytest.mark.parametrize('kwargs', [
    dict(min_value=10 ** 5, width=16),
    dict(max_value=10 ** 5, width=16),
    dict(min_value=10 ** 40, width=32),
    dict(max_value=10 ** 40, width=32),
    dict(min_value=10 ** 400, width=64),
    dict(max_value=10 ** 400, width=64),
    dict(min_value=10 ** 400),
    dict(max_value=10 ** 400),
])
def test_out_of_range(kwargs):
    if kwargs.get('width') == 16 and not (CAN_PACK_HALF_FLOAT or numpy):
        pytest.skip()
    with pytest.raises(OverflowError):
        st.floats(**kwargs).validate()


def test_invalidargument_iff_half_float_unsupported():
    if numpy is None and not CAN_PACK_HALF_FLOAT:
        with pytest.raises(InvalidArgument):
            st.floats(width=16).validate()
    else:
        st.floats(width=16).validate()


def test_disallowed_width():
    with pytest.raises(InvalidArgument):
        st.floats(width=128).validate()


def test_no_single_floats_in_range():
    low = 2. ** 25 + 1
    high = low + 2
    st.floats(low, high).validate()  # Note: OK for 64bit floats
    with pytest.raises(InvalidArgument):
        """Unrepresentable bounds are deprecated; but we're not testing that
        here."""
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            st.floats(low, high, width=32).validate()
