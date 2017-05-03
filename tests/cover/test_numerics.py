# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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
import decimal

import pytest

from hypothesis import given, assume
from tests.common.utils import fails
from hypothesis.strategies import decimals, fractions
from hypothesis.internal.compat import float_to_decimal


@fails
@given(decimals())
def test_all_decimals_can_be_exact_floats(x):
    assume(x.is_finite())
    assert float_to_decimal(float(x)) == x


@given(fractions(), fractions(), fractions())
def test_fraction_addition_is_well_behaved(x, y, z):
    assert x + y + z == y + x + z


@fails
@given(decimals())
def test_decimals_include_nan(x):
    assert not math.isnan(x)


@fails
@given(decimals())
def test_decimals_include_inf(x):
    assume(not x.is_snan())
    assert not math.isinf(x)


@given(decimals(allow_nan=False))
def test_decimals_can_disallow_nan(x):
    assert not math.isnan(x)


@given(decimals(allow_infinity=False))
def test_decimals_can_disallow_inf(x):
    assume(not x.is_snan())
    assert not math.isinf(x)


@pytest.mark.parametrize('places', range(10))
def test_decimals_have_correct_places(places):
    @given(decimals(0, 10, allow_nan=False, places=places))
    def inner_tst(n):
        assert n.as_tuple().exponent == -places
    inner_tst()


@given(decimals(min_value='0.1', max_value='0.2', allow_nan=False, places=1))
def test_works_with_few_values(dec):
    assert dec in (decimal.Decimal('0.1'), decimal.Decimal('0.2'))
