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

from tests.array_api.common import MIN_VER_FOR_COMPLEX
from tests.common.debug import assert_all_examples, find_any, minimal


@pytest.mark.parametrize(
    ("strat_name", "dtype_names"),
    [
        ("integer_dtypes", INT_NAMES),
        ("unsigned_integer_dtypes", UINT_NAMES),
        ("floating_dtypes", FLOAT_NAMES),
        ("real_dtypes", REAL_NAMES),
        pytest.param(
            "complex_dtypes",
            COMPLEX_NAMES,
            marks=pytest.mark.xp_min_version(MIN_VER_FOR_COMPLEX),
        ),
    ],
)
def test_all_generated_dtypes_are_of_group(xp, xps, strat_name, dtype_names):
    """Strategy only generates expected dtypes."""
    strat_func = getattr(xps, strat_name)
    dtypes = [getattr(xp, n) for n in dtype_names]
    assert_all_examples(strat_func(), lambda dtype: dtype in dtypes)


def test_all_generated_scalar_dtypes_are_scalar(xp, xps):
    """Strategy only generates scalar dtypes."""
    if xps.api_version > "2021.12":
        dtypes = [getattr(xp, n) for n in DTYPE_NAMES]
    else:
        dtypes = [getattr(xp, n) for n in ("bool", *REAL_NAMES)]
    assert_all_examples(xps.scalar_dtypes(), lambda dtype: dtype in dtypes)


def test_all_generated_numeric_dtypes_are_numeric(xp, xps):
    """Strategy only generates numeric dtypes."""
    if xps.api_version > "2021.12":
        dtypes = [getattr(xp, n) for n in NUMERIC_NAMES]
    else:
        dtypes = [getattr(xp, n) for n in REAL_NAMES]
    assert_all_examples(xps.numeric_dtypes(), lambda dtype: dtype in dtypes)


def skipif_unsupported_complex(strat_name, dtype_name):
    if not dtype_name.startswith("complex"):
        return strat_name, dtype_name
    mark = pytest.mark.xp_min_version(MIN_VER_FOR_COMPLEX)
    return pytest.param(strat_name, dtype_name, marks=mark)


@pytest.mark.parametrize(
    ("strat_name", "dtype_name"),
    [
        *[skipif_unsupported_complex("scalar_dtypes", n) for n in DTYPE_NAMES],
        *[skipif_unsupported_complex("numeric_dtypes", n) for n in NUMERIC_NAMES],
        *[("integer_dtypes", n) for n in INT_NAMES],
        *[("unsigned_integer_dtypes", n) for n in UINT_NAMES],
        *[("floating_dtypes", n) for n in FLOAT_NAMES],
        *[("real_dtypes", n) for n in REAL_NAMES],
        *[skipif_unsupported_complex("complex_dtypes", n) for n in COMPLEX_NAMES],
    ],
)
def test_strategy_can_generate_every_dtype(xp, xps, strat_name, dtype_name):
    """Strategy generates every expected dtype."""
    strat_func = getattr(xps, strat_name)
    dtype = getattr(xp, dtype_name)
    find_any(strat_func(), lambda d: d == dtype)


def test_minimise_scalar_dtypes(xp, xps):
    """Strategy minimizes to bool dtype."""
    assert minimal(xps.scalar_dtypes()) == xp.bool


@pytest.mark.parametrize(
    "strat_name, sizes",
    [
        ("integer_dtypes", 8),
        ("unsigned_integer_dtypes", 8),
        ("floating_dtypes", 32),
        pytest.param(
            "complex_dtypes", 64, marks=pytest.mark.xp_min_version(MIN_VER_FOR_COMPLEX)
        ),
    ],
)
def test_can_specify_sizes_as_an_int(xp, xps, strat_name, sizes):
    """Strategy treats ints as a single size."""
    strat_func = getattr(xps, strat_name)
    strat = strat_func(sizes=sizes)
    find_any(strat)
