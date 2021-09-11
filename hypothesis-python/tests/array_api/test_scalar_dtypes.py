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

import pytest

from hypothesis import given
from hypothesis.extra.array_api import DTYPE_NAMES, INT_NAMES, NUMERIC_NAMES, UINT_NAMES

from tests.array_api.common import xp, xps
from tests.common.debug import minimal

pytestmark = [pytest.mark.mockable_xp]


@given(xps.scalar_dtypes())
def test_can_generate_scalar_dtypes(dtype):
    assert dtype in (getattr(xp, name) for name in DTYPE_NAMES)


@given(xps.boolean_dtypes())
def test_can_generate_boolean_dtypes(dtype):
    assert dtype == xp.bool


@given(xps.numeric_dtypes())
def test_can_generate_numeric_dtypes(dtype):
    assert dtype in (getattr(xp, name) for name in NUMERIC_NAMES)


@given(xps.integer_dtypes())
def test_can_generate_integer_dtypes(dtype):
    assert dtype in (getattr(xp, name) for name in INT_NAMES)


@given(xps.unsigned_integer_dtypes())
def test_can_generate_unsigned_integer_dtypes(dtype):
    assert dtype in (getattr(xp, name) for name in UINT_NAMES)


@given(xps.floating_dtypes())
def test_can_generate_floating_dtypes(dtype):
    assert dtype in (getattr(xp, name) for name in DTYPE_NAMES)


def test_minimise_scalar_dtypes():
    assert minimal(xps.scalar_dtypes()) == xp.bool


@pytest.mark.parametrize(
    "strat_func, sizes",
    [
        (xps.integer_dtypes, 8),
        (xps.unsigned_integer_dtypes, 8),
        (xps.floating_dtypes, 32),
    ],
)
def test_can_specify_sizes_as_an_int(strat_func, sizes):
    strat_func(sizes=sizes).example()
