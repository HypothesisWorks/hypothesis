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

from hypothesis import given, assume
from tests.common.utils import fails
from hypothesis.strategies import decimals, fractions
from hypothesis.internal.debug import minimal


def is_integral(d):
    if d.is_infinite() or d.is_nan():
        return False
    return d == int(d)


def test_can_find_things_divisible_by_5():
    assert minimal(
        decimals(),
        lambda x: is_integral(x * 5) and not is_integral(x * 2)
    ) == Decimal('0.2')


@fails
@given(decimals())
def test_all_decimals_can_be_exact_floats(x):
    assume(x.is_finite())
    assert Decimal(float(x)) == x


@given(fractions(), fractions(), fractions())
def test_fraction_addition_is_well_behaved(x, y, z):
    assert x + y + z == y + x + z
