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

from hypothesis.extra.array_api import (
    COMPLEX_NAMES,
    DTYPE_NAMES,
    FLOAT_NAMES,
    INT_NAMES,
    NUMERIC_NAMES,
    REAL_NAMES,
    UINT_NAMES,
)

from tests.common.debug import assert_all_examples, find_any, minimal


def test_can_generate_scalar_dtypes(xp, xps):
    dtypes = [getattr(xp, name) for name in DTYPE_NAMES]
    assert_all_examples(xps.scalar_dtypes(), lambda dtype: dtype in dtypes)


def test_can_generate_boolean_dtypes(xp, xps):
    assert_all_examples(xps.boolean_dtypes(), lambda dtype: dtype == xp.bool)


def test_can_generate_numeric_dtypes(xp, xps):
    numeric_dtypes = [getattr(xp, name) for name in NUMERIC_NAMES]
    assert_all_examples(xps.numeric_dtypes(), lambda dtype: dtype in numeric_dtypes)


def test_can_generate_integer_dtypes(xp, xps):
    int_dtypes = [getattr(xp, name) for name in INT_NAMES]
    assert_all_examples(xps.integer_dtypes(), lambda dtype: dtype in int_dtypes)


def test_can_generate_unsigned_integer_dtypes(xp, xps):
    uint_dtypes = [getattr(xp, name) for name in UINT_NAMES]
    assert_all_examples(
        xps.unsigned_integer_dtypes(), lambda dtype: dtype in uint_dtypes
    )


def test_can_generate_floating_dtypes(xp, xps):
    float_dtypes = [getattr(xp, name) for name in FLOAT_NAMES]
    assert_all_examples(xps.floating_dtypes(), lambda dtype: dtype in float_dtypes)


def test_can_generate_real_dtypes(xp, xps):
    real_dtypes = [getattr(xp, name) for name in REAL_NAMES]
    assert_all_examples(xps.real_dtypes(), lambda dtype: dtype in real_dtypes)


@pytest.mark.xp_min_version("draft")
def test_can_generate_complex_dtypes(xp, xps):
    complex_dtypes = [getattr(xp, name) for name in COMPLEX_NAMES]
    assert_all_examples(xps.complex_dtypes(), lambda dtype: dtype in complex_dtypes)


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
    strat = strat_func(sizes=sizes)
    find_any(strat)
