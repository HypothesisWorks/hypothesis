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

"""Tests for being able to generate weird and wonderful floating point
numbers."""


from __future__ import division, print_function, absolute_import

import sys
import math

from hypothesis import seed, given, assume, reject, settings
from hypothesis.errors import Unsatisfiable
from tests.common.utils import fails
from hypothesis.strategies import lists, floats, integers

TRY_HARDER = settings(max_examples=1000, max_iterations=2000)


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
    assume(not (math.isinf(x) or math.isnan(x)))
    assert x == int(x)


@fails
@given(floats())
@TRY_HARDER
def test_is_not_int(x):
    assume(not (math.isinf(x) or math.isnan(x)))
    assert x != int(x)


@fails
@given(floats())
@TRY_HARDER
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
@given(floats())
@TRY_HARDER
def test_can_generate_really_small_positive_floats(x):
    assume(x > 0)
    assert x >= REALLY_SMALL_FLOAT


@fails
@given(floats())
@TRY_HARDER
def test_can_generate_really_small_negative_floats(x):
    assume(x < 0)
    assert x <= -REALLY_SMALL_FLOAT


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


@given(floats(), floats(), integers())
def test_floats_are_in_range(x, y, s):
    assume(not (math.isnan(x) or math.isnan(y)))
    assume(not (math.isinf(x) or math.isinf(y)))
    x, y = sorted((x, y))
    assume(x < y)

    @given(floats(x, y))
    @seed(s)
    @settings(max_examples=10)
    def test_is_in_range(t):
        assert x <= t <= y

    try:
        test_is_in_range()
    except Unsatisfiable:
        reject()
