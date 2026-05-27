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

import pytest

from hypothesis.extra.array_api import find_castable_builtin_for_dtype
from hypothesis.internal.floats import width_smallest_normals

from tests.array_api.common import dtype_name_params, flushes_to_zero
from tests.common.debug import (
    assert_all_examples,
    assert_no_examples,
    find_any,
    minimal,
)


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


smallest_normal = width_smallest_normals[32]


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
