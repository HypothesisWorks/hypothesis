# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis import given, assume
from tests.common.utils import fails
from hypothesis.strategies import decimals, fractions, float_to_decimal


@fails
@given(decimals())
def test_all_decimals_can_be_exact_floats(x):
    assume(x.is_finite())
    assert float_to_decimal(float(x)) == x


@given(fractions(), fractions(), fractions())
def test_fraction_addition_is_well_behaved(x, y, z):
    assert x + y + z == y + x + z
