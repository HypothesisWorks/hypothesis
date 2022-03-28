# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import given
from hypothesis.extra.array_api import DTYPE_NAMES, INT_NAMES, NUMERIC_NAMES, UINT_NAMES

from tests.common.debug import minimal


def test_can_generate_scalar_dtypes(xp, xps):
    @given(xps.scalar_dtypes())
    def test(dtype):
        assert dtype in (getattr(xp, name) for name in DTYPE_NAMES)

    test()


def test_can_generate_boolean_dtypes(xp, xps):
    @given(xps.boolean_dtypes())
    def test(dtype):
        assert dtype == xp.bool

    test()


def test_can_generate_numeric_dtypes(xp, xps):
    @given(xps.numeric_dtypes())
    def test(dtype):
        assert dtype in (getattr(xp, name) for name in NUMERIC_NAMES)

    test()


def test_can_generate_integer_dtypes(xp, xps):
    @given(xps.integer_dtypes())
    def test(dtype):
        assert dtype in (getattr(xp, name) for name in INT_NAMES)

    test()


def test_can_generate_unsigned_integer_dtypes(xp, xps):
    @given(xps.unsigned_integer_dtypes())
    def test(dtype):
        assert dtype in (getattr(xp, name) for name in UINT_NAMES)

    test()


def test_can_generate_floating_dtypes(xp, xps):
    @given(xps.floating_dtypes())
    def test(dtype):
        assert dtype in (getattr(xp, name) for name in DTYPE_NAMES)

    test()


def test_minimise_scalar_dtypes(xp, xps):
    assert minimal(xps.scalar_dtypes()) == xp.bool


@pytest.mark.parametrize(
    "strat_name, sizes",
    [
        ("integer_dtypes", 8),
        ("unsigned_integer_dtypes", 8),
        ("floating_dtypes", 32),
    ],
)
def test_can_specify_sizes_as_an_int(xp, xps, strat_name, sizes):
    strat_func = getattr(xps, strat_name)
    strat_func(sizes=sizes).example()
