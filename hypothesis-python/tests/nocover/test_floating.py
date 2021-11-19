# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

"""Tests for being able to generate weird and wonderful floating point numbers."""

import math
from itertools import product
from sys import float_info

import pytest
from tests.common.debug import assert_all_examples, assert_no_examples, find_any
from tests.common.utils import fails

from hypothesis import HealthCheck, assume, given, settings
from hypothesis.internal.floats import float_to_int, next_down
from hypothesis.errors import InvalidArgument
from hypothesis.internal.floats import next_down, next_up
from hypothesis.strategies import data, floats, lists

TRY_HARDER = settings(
    max_examples=1000, suppress_health_check=[HealthCheck.filter_too_much]
)


@given(floats())
@TRY_HARDER
def test_is_float(x):
    assert isinstance(x, float)


@fails
@given(floats())
@TRY_HARDER
def test_inversion_is_imperfect(x):
    assume(x != 0.0)
    y = 1.0 / x
    assert x * y == 1.0


@given(floats(-float_info.max, float_info.max))
def test_largest_range(x):
    assert not math.isinf(x)


@given(floats())
@TRY_HARDER
def test_negation_is_self_inverse(x):
    assume(not math.isnan(x))
    y = -x
    assert -y == x


@fails
@given(lists(floats()))
def test_is_not_nan(xs):
    assert not any(math.isnan(x) for x in xs)


@fails
@given(floats())
@TRY_HARDER
def test_is_not_positive_infinite(x):
    assume(x > 0)
    assert not math.isinf(x)


@fails
@given(floats())
@TRY_HARDER
def test_is_not_negative_infinite(x):
    assume(x < 0)
    assert not math.isinf(x)


@fails
@given(floats())
@TRY_HARDER
def test_is_int(x):
    assume(math.isfinite(x))
    assert x == int(x)


@fails
@given(floats())
@TRY_HARDER
def test_is_not_int(x):
    assume(math.isfinite(x))
    assert x != int(x)


@fails
@given(floats())
@TRY_HARDER
def test_is_in_exact_int_range(x):
    assume(math.isfinite(x))
    assert x + 1 != x


# Tests whether we can represent subnormal floating point numbers.
# IEE-754 requires subnormal support, but it's often disabled anyway by unsafe
# compiler options like `-ffast-math`.  On most hardware that's even a global
# config option, so *linking against* something built this way can break us.
# Everything is terrible
FLUSH_SUBNORMALS_TO_ZERO = next_down(float_info.min) == 0.0


def test_compiled_with_sane_math_options():
    # Checks that we're not unexpectedly skipping the subnormal tests below.
    assert not FLUSH_SUBNORMALS_TO_ZERO


@pytest.mark.skipif(FLUSH_SUBNORMALS_TO_ZERO, reason="broken by unsafe compiler flags")
@fails
@given(floats())
@TRY_HARDER
def test_can_generate_really_small_positive_floats(x):
    assume(x > 0)
    assert x >= float_info.min


@pytest.mark.skipif(FLUSH_SUBNORMALS_TO_ZERO, reason="broken by unsafe compiler flags")
@fails
@given(floats())
@TRY_HARDER
def test_can_generate_really_small_negative_floats(x):
    assume(x < 0)
    assert x <= -float_info.min


@pytest.mark.parametrize(
    "min_value, max_value",
    [
        (None, None),
        (-1, 0),
        (0, 1),
        (-1, 1),
    ],
)
@pytest.mark.parametrize(
    "width, smallest_normal",
    [(16, 2 ** -14), (32, 2 ** -126), (64, 2 ** -1022)],
    ids=["16", "32", "64"],
)
def test_does_not_generate_subnormals_when_disallowed(
    width,
    smallest_normal,
    min_value,
    max_value,
):
    strat = floats(
        min_value=min_value,
        max_value=max_value,
        allow_subnormal=False,
        width=width,
    )
    strat = strat.filter(lambda x: x != 0.0 and not math.isnan(x) and not math.isinf(x))
    assert_all_examples(strat, lambda x: x <= -smallest_normal or x >= smallest_normal)


def kw(**kwargs):
    id_ = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    return pytest.param(kwargs, id=id_)


@pytest.mark.skipif(FLUSH_SUBNORMALS_TO_ZERO, reason="broken by unsafe compiler flags")
@pytest.mark.parametrize(
    "kwargs",
    [
        kw(min_value=1),
        kw(min_value=1),
        kw(max_value=-1),
        kw(min_value=float_info.min),
        kw(min_value=next_down(float_info.min), exclude_min=True),
        kw(max_value=-float_info.min),
        kw(min_value=next_up(-float_info.min), exclude_max=True),
    ],
)
def test_subnormal_validation(kwargs):
    strat = floats(**kwargs, allow_subnormal=True)
    with pytest.raises(InvalidArgument):
        strat.example()


@pytest.mark.skipif(FLUSH_SUBNORMALS_TO_ZERO, reason="broken by unsafe compiler flags")
@pytest.mark.parametrize(
    "kwargs",
    [
        # min value
        kw(allow_subnormal=False, min_value=1),
        kw(allow_subnormal=False, min_value=float_info.min),
        kw(allow_subnormal=True, min_value=-1),
        kw(allow_subnormal=True, min_value=next_down(float_info.min)),
        # max value
        kw(allow_subnormal=False, max_value=-1),
        kw(allow_subnormal=False, max_value=-float_info.min),
        kw(allow_subnormal=True, max_value=1),
        kw(allow_subnormal=True, max_value=next_up(-float_info.min)),
        # min/max values
        kw(allow_subnormal=True, min_value=-1, max_value=1),
        kw(
            allow_subnormal=True,
            min_value=next_down(float_info.min),
            max_value=float_info.min,
        ),
        kw(
            allow_subnormal=True,
            min_value=-float_info.min,
            max_value=next_up(-float_info.min),
        ),
        kw(allow_subnormal=False, min_value=-1, max_value=-float_info.min),
        kw(allow_subnormal=False, min_value=float_info.min, max_value=1),
    ],
)
def test_allow_subnormal_defaults_correctly(kwargs):
    allow_subnormal = kwargs["allow_subnormal"]
    del kwargs["allow_subnormal"]
    strat = floats(**kwargs).filter(lambda x: x != 0)
    if allow_subnormal:
        find_any(
            strat,
            lambda x: -float_info.min < x < float_info.min,
        )
    else:
        assert_no_examples(strat, lambda x: -float_info.min < x < float_info.min)


@fails
@given(floats())
@TRY_HARDER
def test_can_find_floats_that_do_not_round_trip_through_strings(x):
    assert float(str(x)) == x


@fails
@given(floats())
@TRY_HARDER
def test_can_find_floats_that_do_not_round_trip_through_reprs(x):
    assert float(repr(x)) == x


finite_floats = floats(allow_infinity=False, allow_nan=False)


@settings(deadline=None)
@given(finite_floats, finite_floats, data())
def test_floats_are_in_range(x, y, data):
    x, y = sorted((x, y))
    assume(x < y)

    t = data.draw(floats(x, y))
    assert x <= t <= y


@pytest.mark.parametrize("neg", [False, True])
@pytest.mark.parametrize("snan", [False, True])
def test_can_find_negative_and_signaling_nans(neg, snan):
    find_any(
        floats().filter(math.isnan),
        lambda x: (
            snan is (float_to_int(abs(x)) != float_to_int(float("nan")))
            and neg is (math.copysign(1, x) == -1)
        ),
        settings=TRY_HARDER,
    )
