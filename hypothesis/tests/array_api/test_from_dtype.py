# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math
from copy import copy

import numpy as np
import pytest

from hypothesis.errors import HypothesisWarning, InvalidArgument
from hypothesis.extra.array_api import (
    _from_dtype,
    dtype_from_name,
    find_castable_builtin_for_dtype,
    mock_xp,
)
from hypothesis.internal.floats import width_smallest_normals

from tests.array_api.common import (
    MIN_VER_FOR_COMPLEX,
    dtype_name_params,
    flushes_to_zero,
)
from tests.common.debug import (
    assert_all_examples,
    assert_no_examples,
    check_can_generate_examples,
    find_any,
    minimal,
)


def _xp_without(*attrs):
    """A copy of mock_xp with the given attributes removed."""
    xp = copy(mock_xp)
    for attr in attrs:
        delattr(xp, attr)
    return xp


@pytest.mark.parametrize("dtype_name", dtype_name_params)
def test_strategies_have_reusable_values(xp, xps, dtype_name):
    """Inferred strategies have reusable values."""
    strat = xps.from_dtype(dtype_name)
    assert strat.has_reusable_values


@pytest.mark.parametrize("dtype_name", dtype_name_params)
def test_produces_castable_instances_from_dtype(xp, xps, dtype_name):
    """Strategies inferred by dtype generate values of a builtin type castable
    to the dtype."""
    dtype = getattr(xp, dtype_name)
    builtin = find_castable_builtin_for_dtype(xp, xps.api_version, dtype)
    assert_all_examples(xps.from_dtype(dtype), lambda v: isinstance(v, builtin))


@pytest.mark.parametrize("dtype_name", dtype_name_params)
def test_produces_castable_instances_from_name(xp, xps, dtype_name):
    """Strategies inferred by dtype name generate values of a builtin type
    castable to the dtype."""
    dtype = getattr(xp, dtype_name)
    builtin = find_castable_builtin_for_dtype(xp, xps.api_version, dtype)
    assert_all_examples(xps.from_dtype(dtype_name), lambda v: isinstance(v, builtin))


@pytest.mark.parametrize("dtype_name", dtype_name_params)
def test_passing_inferred_strategies_in_arrays(xp, xps, dtype_name):
    """Inferred strategies usable in arrays strategy."""
    elements = xps.from_dtype(dtype_name)
    find_any(xps.arrays(dtype_name, 10, elements=elements))


@pytest.mark.parametrize(
    "dtype, kwargs, predicate",
    [
        # Floating point: bounds, exclusive bounds, and excluding nonfinites
        ("float32", {"min_value": 1, "max_value": 2}, lambda x: 1 <= x <= 2),
        (
            "float32",
            {"min_value": 1, "max_value": 2, "exclude_min": True, "exclude_max": True},
            lambda x: 1 < x < 2,
        ),
        ("float32", {"allow_nan": False}, lambda x: not math.isnan(x)),
        ("float32", {"allow_infinity": False}, lambda x: not math.isinf(x)),
        ("float32", {"allow_nan": False, "allow_infinity": False}, math.isfinite),
        # Integer bounds, limited to the representable range
        ("int8", {"min_value": -1, "max_value": 1}, lambda x: -1 <= x <= 1),
        ("uint8", {"min_value": 1, "max_value": 2}, lambda x: 1 <= x <= 2),
    ],
)
def test_from_dtype_with_kwargs(xp, xps, dtype, kwargs, predicate):
    """Strategies inferred with kwargs generate values in bounds."""
    strat = xps.from_dtype(dtype, **kwargs)
    assert_all_examples(strat, predicate)


def test_can_minimize_floats(xp, xps):
    """Inferred float strategy minimizes to a good example."""
    smallest = minimal(xps.from_dtype(xp.float32), lambda n: n >= 1.0)
    # TODO_IR should be resolved by float widths on the ir, see other TODO_IR comments
    assert smallest in {1, math.inf}


smallest_normal = width_smallest_normals(32)


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"min_value": -1},
        {"max_value": 1},
        {"min_value": -1, "max_value": 1},
    ],
)
def test_subnormal_generation(xp, xps, kwargs):
    """Generation of subnormals is dependent on FTZ behaviour of array module."""
    strat = xps.from_dtype(xp.float32, **kwargs).filter(lambda n: n != 0)
    if flushes_to_zero(xp, width=32):
        assert_no_examples(strat, lambda n: -smallest_normal < n < smallest_normal)
    else:
        find_any(strat, lambda n: -smallest_normal < n < smallest_normal)


def test_infers_flush_to_zero_from_asarray():
    """from_dtype() infers allow_subnormal=False when the array module's
    asarray() flushes subnormal floats to zero."""

    def _ftz_asarray(obj, dtype=None):
        """Like np.asarray(), but flushes subnormal floats to zero"""
        arr = np.asarray(obj, dtype=dtype)
        if np.issubdtype(arr.dtype, np.floating):
            tiny = np.finfo(arr.dtype).tiny
            arr = np.where((arr != 0) & (np.abs(arr) < tiny), arr.dtype.type(0), arr)
        return arr

    xp = copy(mock_xp)
    xp.asarray = _ftz_asarray
    strat = _from_dtype(xp, "draft", xp.float32).filter(lambda n: n != 0)
    assert_no_examples(strat, lambda n: -smallest_normal < n < smallest_normal)


@pytest.mark.xp_min_version(MIN_VER_FOR_COMPLEX)
@pytest.mark.parametrize("allow_subnormal", [True, False])
def test_complex_from_dtype_respects_explicit_allow_subnormal(xp, xps, allow_subnormal):
    """from_dtype() does not need to infer FTZ behaviour for complex dtypes
    when allow_subnormal is passed explicitly."""
    strat = xps.from_dtype(xp.complex64, allow_subnormal=allow_subnormal)
    check_can_generate_examples(strat)


def test_ignores_missing_bool_dtype():
    """find_castable_builtin_for_dtype() tolerates an array module with no
    bool dtype, so long as the dtype being looked up is found elsewhere."""
    xp = _xp_without("bool")
    builtin = find_castable_builtin_for_dtype(xp, "draft", xp.int8)
    assert builtin is int


def test_warns_and_raises_for_unrecognised_dtype_with_missing_dtypes():
    """An unrecognised dtype raises InvalidArgument, with a warning listing
    any dtypes missing from the array module - even for api_version=2021.12,
    when complex dtypes are not considered at all."""
    xp = _xp_without("float64")
    with (
        pytest.warns(HypothesisWarning, match=f"{mock_xp.__name__}.*float64"),
        pytest.raises(InvalidArgument, match="not recognised"),
    ):
        find_castable_builtin_for_dtype(xp, "2021.12", object())


def test_dtype_from_name_raises_for_dtype_missing_from_xp():
    """dtype_from_name() raises a helpful error when the array module lacks
    the named (but otherwise valid) dtype."""
    xp = _xp_without("float64")
    with pytest.raises(InvalidArgument, match=f"{mock_xp.__name__}.*float64"):
        dtype_from_name(xp, "float64")


def test_dtype_from_name_raises_for_invalid_name():
    """dtype_from_name() raises a helpful error for names that are not valid
    Array API dtypes."""
    with pytest.raises(InvalidArgument, match="not a valid Array API data type"):
        dtype_from_name(mock_xp, "int7")
