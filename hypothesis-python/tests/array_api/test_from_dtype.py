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

from tests.array_api.common import xp, xps
from tests.common.debug import minimal

pytestmark = [pytest.mark.mockable_xp]


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
        (
            xp.float32,
            {"allow_nan": False, "allow_infinity": False},
            lambda x: not math.isnan(x) and not math.isinf(x),
        ),
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
    assert smallest in (1, 50)
