# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from decimal import Decimal
from fractions import Fraction

from hypothesis import given, assume
from tests.common.utils import fails


@fails
@given(Decimal)
def test_all_decimals_can_be_exact_floats(x):
    assume(x.is_finite())
    assert Decimal(float(x)) == x


@fails
@given([Decimal])
def test_reversing_preserves_decimal_addition(xs):
    assert sum(xs) == sum(reversed(xs))


@given([Fraction])
def test_reversing_preserves_fraction_addition(xs):
    assert sum(xs) == sum(reversed(xs))
