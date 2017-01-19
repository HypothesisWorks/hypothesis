# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

import math

from hypothesis import given, assume
from tests.common.utils import fails, fails_with
from hypothesis.strategies import decimals, fractions, float_to_decimal


@fails
@given(decimals())
def test_all_decimals_can_be_exact_floats(x):
    assume(x.is_finite())
    assert float_to_decimal(float(x)) == x


@given(fractions(), fractions(), fractions())
def test_fraction_addition_is_well_behaved(x, y, z):
    assert x + y + z == y + x + z


@fails_with(AssertionError)
@given(decimals())
def test_decimals_include_nan(x):
    assert not math.isnan(x)


@fails_with(AssertionError)
@given(decimals())
def test_decimals_include_inf(x):
    assert not math.isinf(x)


@given(decimals(allow_nan=False))
def test_decimals_can_disallow_nan(x):
    assert not math.isnan(x)


@given(decimals(allow_infinity=False))
def test_decimals_can_disallow_inf(x):
    assert not math.isinf(x)
