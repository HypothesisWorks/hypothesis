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

import math

import pytest

from hypothesis import given, strategies as st
from hypothesis.extra.array_api import DTYPE_NAMES, find_castable_builtin_for_dtype
from hypothesis.internal.floats import width_smallest_normals

from tests.array_api.common import WIDTHS_FTZ, xp, xps
from tests.common.debug import assert_no_examples, find_any, minimal


@given(xps.scalar_dtypes())
def test_strategies_have_reusable_values(dtype):
    """Inferred strategies have reusable values."""
    strat = xps.from_dtype(dtype)
    assert strat.has_reusable_values


DTYPES = [getattr(xp, name) for name in DTYPE_NAMES]


@pytest.mark.parametrize("dtype", DTYPES)
def test_produces_castable_instances_from_dtype(dtype):
    """Strategies inferred by dtype generate values of a builtin type castable
    to the dtype."""
    builtin = find_castable_builtin_for_dtype(xp, dtype)

    @given(xps.from_dtype(dtype))
    def test_is_builtin(value):
        assert isinstance(value, builtin)

    test_is_builtin()


@pytest.mark.parametrize("name", DTYPE_NAMES)
def test_produces_castable_instances_from_name(name):
    """Strategies inferred by dtype name generate values of a builtin type
    castable to the dtype."""
    builtin = find_castable_builtin_for_dtype(xp, getattr(xp, name))

    @given(xps.from_dtype(name))
    def test_is_builtin(value):
        assert isinstance(value, builtin)

    test_is_builtin()


@pytest.mark.parametrize("dtype", DTYPES)
def test_passing_inferred_strategies_in_arrays(dtype):
    """Inferred strategies usable in arrays strategy."""
    elements = xps.from_dtype(dtype)

    @given(xps.arrays(dtype, 10, elements=elements))
    def smoke_test(_):
        pass

    smoke_test()


@pytest.mark.parametrize(
    "dtype, kwargs, predicate",
    [
        # Floating point: bounds, exclusive bounds, and excluding nonfinites
        (xp.float32, {"min_value": 1, "max_value": 2}, lambda x: 1 <= x <= 2),
        (
            xp.float32,
            {"min_value": 1, "max_value": 2, "exclude_min": True, "exclude_max": True},
            lambda x: 1 < x < 2,
        ),
        (xp.float32, {"allow_nan": False}, lambda x: not math.isnan(x)),
        (xp.float32, {"allow_infinity": False}, lambda x: not math.isinf(x)),
        (xp.float32, {"allow_nan": False, "allow_infinity": False}, math.isfinite),
        # Integer bounds, limited to the representable range
        (xp.int8, {"min_value": -1, "max_value": 1}, lambda x: -1 <= x <= 1),
        (xp.uint8, {"min_value": 1, "max_value": 2}, lambda x: 1 <= x <= 2),
    ],
)
@given(data=st.data())
def test_from_dtype_with_kwargs(data, dtype, kwargs, predicate):
    """Strategies inferred with kwargs generate values in bounds."""
    strat = xps.from_dtype(dtype, **kwargs)
    value = data.draw(strat)
    assert predicate(value)


def test_can_minimize_floats():
    """Inferred float strategy minimizes to a good example."""
    smallest = minimal(xps.from_dtype(xp.float32), lambda n: n >= 1.0)
    assert smallest == 1


smallest_normal = width_smallest_normals[32]
subnormal_strats = [
    xps.from_dtype(xp.float32),
    xps.from_dtype(xp.float32, min_value=-1),
    xps.from_dtype(xp.float32, max_value=1),
    xps.from_dtype(xp.float32, max_value=1),
    pytest.param(
        xps.from_dtype(xp.float32, min_value=-1, max_value=1),
        marks=pytest.mark.skip(
            reason="FixedBoundFloatStrategy(0, 1) rarely generates subnormals"
        ),
    ),
]


@pytest.mark.skipif(
    WIDTHS_FTZ[32], reason="Subnormals should not be generated for FTZ builds"
)
@pytest.mark.parametrize("strat", subnormal_strats)
def test_generate_subnormals_for_non_ftz_float32(strat):
    find_any(
        strat.filter(lambda n: n != 0), lambda n: -smallest_normal < n < smallest_normal
    )


@pytest.mark.skipif(
    not WIDTHS_FTZ[32], reason="Subnormals should be generated for non-FTZ builds"
)
@pytest.mark.parametrize("strat", subnormal_strats)
def test_does_not_generate_subnormals_for_ftz_float32(strat):
    assert_no_examples(
        strat.filter(lambda n: n != 0), lambda n: -smallest_normal < n < smallest_normal
    )
