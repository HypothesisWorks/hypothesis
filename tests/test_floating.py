# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""Tests for being able to generate weird and wonderful floating point
numbers."""

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import sys
import math

from hypothesis import given, assume
from tests.common.utils import fails
from hypothesis.internal.utils.fixers import actually_equal


@fails
@given(float)
def test_inversion_is_imperfect(x):
    assume(x != 0.0)
    y = 1.0 / x
    assert x * y == 1.0


@given(float)
def test_negation_is_self_inverse(x):
    assume(not math.isnan(x))
    y = -x
    assert -y == x


@fails
@given(float)
def test_is_not_nan(x):
    assert not math.isnan(x)


@fails
@given(float)
def test_is_not_positive_infinite(x):
    assume(x > 0)
    assert not math.isinf(x)


@fails
@given(float)
def test_is_not_negative_infinite(x):
    assume(x < 0)
    assert not math.isinf(x)


@fails
@given(float)
def test_is_int(x):
    assume(not (math.isinf(x) or math.isnan(x)))
    assert x == int(x)


@fails
@given(float)
def test_is_not_int(x):
    assume(not (math.isinf(x) or math.isnan(x)))
    assert x != int(x)


@fails
@given(float)
def test_is_in_exact_int_range(x):
    assume(not (math.isinf(x) or math.isnan(x)))
    assert x + 1 != x


# Tests whether we can represent subnormal floating point numbers.
# This is essentially a function of how the python interpreter
# was compiled.
# Everything is terrible
if math.ldexp(0.25, -1022) > 0:
    REALLY_SMALL_FLOAT = sys.float_info.min
else:
    REALLY_SMALL_FLOAT = sys.float_info.min * 2


@fails
@given(float)
def test_can_generate_really_small_positive_floats(x):
    assume(x > 0)
    assert x >= REALLY_SMALL_FLOAT


@fails
@given(float)
def test_can_generate_really_small_negative_floats(x):
    assume(x < 0)
    assert x <= -REALLY_SMALL_FLOAT


@fails
@given(float)
def test_can_find_floats_that_do_not_round_trip_through_strings(x):
    assert float(str(x)) == x
    assert actually_equal(float(str(x)), x)


@fails
@given(float)
def test_can_find_floats_that_do_not_round_trip_through_reprs(x):
    assert float(repr(x)) == x


@given(float)
def test_printing_and_parsing_is_fuzzy_equal(x):
    assert actually_equal(
        x,
        float(repr(x)),
        fuzzy=True,
    )
