# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for being able to generate weird and wonderful floating point numbers."""

import math
import sys

import pytest

from hypothesis import HealthCheck, assume, given, settings
from hypothesis.internal.floats import float_to_int
from hypothesis.strategies import data, floats, lists

from tests.common.debug import find_any
from tests.common.utils import fails

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


@given(floats(-sys.float_info.max, sys.float_info.max))
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
@TRY_HARDER
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
