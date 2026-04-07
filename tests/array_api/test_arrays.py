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

from hypothesis import given, settings, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.extra.array_api import COMPLEX_NAMES, REAL_NAMES
from hypothesis.internal.floats import width_smallest_normals

from tests.array_api.common import (
    MIN_VER_FOR_COMPLEX,
    dtype_name_params,
    flushes_to_zero,
)
from tests.common.debug import (
    assert_all_examples,
    check_can_generate_examples,
    find_any,
    minimal,
)
from tests.common.utils import flaky


def skip_on_missing_unique_values(xp):
    if not hasattr(xp, "unique_values"):
        pytest.mark.skip("xp.unique_values() is not required to exist")


def xfail_on_indistinct_nans(xp):
    """
    xp.unique_value() should return distinct NaNs - if not, tests that (rightly)
    assume such behaviour will likely fail. For example, NumPy 1.22 treats NaNs
    as indistinct, so tests that use this function will be marked as xfail.
    See https://mail.python.org/pipermail/numpy-discussion/2021-August/081995.html
    """
    skip_on_missing_unique_values(xp)
    two_nans = xp.asarray([float("nan"), float("nan")])
    if xp.unique_values(two_nans).size != 2:
        pytest.xfail("NaNs not distinct")


@pytest.mark.parametrize("dtype_name", dtype_name_params)
def test_draw_arrays_from_dtype(xp, xps, dtype_name):
    """Draw arrays from dtypes."""
    dtype = getattr(xp, dtype_name)
    assert_all_examples(xps.arrays(dtype, ()), lambda x: x.dtype == dtype)


@pytest.mark.parametrize("dtype_name", dtype_name_params)
def test_draw_arrays_from_scalar_names(xp, xps, dtype_name):
    """Draw arrays from dtype names."""
    dtype = getattr(xp, dtype_name)
    assert_all_examples(xps.arrays(dtype_name, ()), lambda x: x.dtype == dtype)


@given(data=st.data())
def test_draw_arrays_from_shapes(xp, xps, data):
    """Draw arrays from shapes."""
    shape = data.draw(xps.array_shapes())
    x = data.draw(xps.arrays(xp.int8, shape))
    assert x.ndim == len(shape)
    assert x.shape == shape


@given(data=st.data())
def test_draw_arrays_from_int_shapes(xp, xps, data):
    """Draw arrays from integers as shapes."""
    size = data.draw(st.integers(0, 10))
    x = data.draw(xps.arrays(xp.int8, size))
    assert x.shape == (size,)


@pytest.mark.parametrize(
    "strat_name",
    [
        "scalar_dtypes",
        "boolean_dtypes",
        "integer_dtypes",
        "unsigned_integer_dtypes",
        "floating_dtypes",
        "real_dtypes",
        pytest.param(
            "complex_dtypes", marks=pytest.mark.xp_min_version(MIN_VER_FOR_COMPLEX)
        ),
    ],
)
def test_draw_arrays_from_dtype_strategies(xp, xps, strat_name):
    """Draw arrays from dtype strategies."""
    strat_func = getattr(xps, strat_name)
    strat = strat_func()
    find_any(xps.arrays(strat, ()))


@settings(deadline=None)
@given(data=st.data())
def test_draw_arrays_from_dtype_name_strategies(xp, xps, data):
    """Draw arrays from dtype name strategies."""
    all_names = ("bool", *REAL_NAMES)
    if xps.api_version > "2021.12":
        all_names += COMPLEX_NAMES
    sample_names = data.draw(
        st.lists(st.sampled_from(all_names), min_size=1, unique=True)
    )
    find_any(xps.arrays(st.sampled_from(sample_names), ()))


def test_generate_arrays_from_shapes_strategy(xp, xps):
    """Generate arrays from shapes strategy."""
    find_any(xps.arrays(xp.int8, xps.array_shapes()))


def test_generate_arrays_from_integers_strategy_as_shape(xp, xps):
    """Generate arrays from integers strategy as shapes strategy."""
    find_any(xps.arrays(xp.int8, st.integers(0, 100)))


def test_generate_arrays_from_zero_dimensions(xp, xps):
    """Generate arrays from empty shape."""
    assert_all_examples(xps.arrays(xp.int8, ()), lambda x: x.shape == ())


@given(data=st.data())
def test_generate_arrays_from_zero_sided_shapes(xp, xps, data):
    """Generate arrays from shapes with at least one 0-sized dimension."""
    shape = data.draw(xps.array_shapes(min_side=0).filter(lambda s: 0 in s))
    arr = data.draw(xps.arrays(xp.int8, shape))
    assert arr.shape == shape


def test_generate_arrays_from_unsigned_ints(xp, xps):
    """Generate arrays from unsigned integer dtype."""
    assert_all_examples(xps.arrays(xp.uint32, (5, 5)), lambda x: xp.all(x >= 0))
    # Ensure we're not just picking non-negative signed integers
    signed_max = xp.iinfo(xp.int32).max
    find_any(xps.arrays(xp.uint32, (5, 5)), lambda x: xp.any(x > signed_max))


def test_generate_arrays_from_0d_arrays(xp, xps):
    """Generate arrays from 0d array elements."""
    assert_all_examples(
        xps.arrays(
            dtype=xp.uint8,
            shape=(5, 5),
            elements=xps.from_dtype(xp.uint8).map(
                lambda e: xp.asarray(e, dtype=xp.uint8)
            ),
        ),
        lambda x: x.shape == (5, 5),
    )


def test_minimize_arrays_with_default_dtype_shape_strategies(xp, xps):
    """Strategy with default scalar_dtypes and array_shapes strategies minimize
    to a boolean 1-dimensional array of size 1."""
    smallest = minimal(xps.arrays(xps.scalar_dtypes(), xps.array_shapes()))
    assert smallest.shape == (1,)
    assert smallest.dtype == xp.bool
    assert not xp.any(smallest)


def test_minimize_arrays_with_0d_shape_strategy(xp, xps):
    """Strategy with shape strategy that can generate empty tuples minimizes to
    0d arrays."""
    smallest = minimal(xps.arrays(xp.int8, xps.array_shapes(min_dims=0)))
    assert smallest.shape == ()


@pytest.mark.parametrize("dtype", dtype_name_params[1:])
def test_minimizes_numeric_arrays(xp, xps, dtype):
    """Strategies with numeric dtypes minimize to zero-filled arrays."""
    smallest = minimal(xps.arrays(dtype, (2, 2)))
    assert xp.all(smallest == 0)


def test_minimize_large_uint_arrays(xp, xps):
    """Strategy with uint dtype and largely sized shape minimizes to a good
    example."""
    if not hasattr(xp, "nonzero"):
        pytest.skip("optional API")
    smallest = minimal(xps.arrays(xp.uint8, 100), lambda x: xp.any(x) and not xp.all(x))
    assert xp.all(xp.logical_or(smallest == 0, smallest == 1))
    idx = xp.nonzero(smallest)[0]
    assert idx.size in (1, smallest.size - 1)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@flaky(max_runs=50, min_passes=1)
def test_minimize_float_arrays(xp, xps):
    """Strategy with float dtype minimizes to a good example.

    We filter runtime warnings and expect flaky array generation for
    specifically NumPy - this behaviour may not be required when testing
    with other array libraries.
    """
    smallest = minimal(xps.arrays(xp.float32, 50), lambda x: xp.sum(x) >= 1.0)
    # TODO_IR the shrinker gets stuck when the first failure is math.inf, because
    # downcasting inf to a float32 overflows, triggering rejection sampling which
    # is then immediately not a shrink (specifically it overruns the attempt data).
    #
    # this should be resolved by adding float widths to the ir.
    assert xp.sum(smallest) in (1, 50) or all(math.isinf(v) for v in smallest)


def test_minimizes_to_fill(xp, xps):
    """Strategy with single fill value minimizes to arrays only containing said
    fill value."""
    smallest = minimal(xps.arrays(xp.float32, 10, fill=st.just(3.0)))
    assert xp.all(smallest == 3.0)


def test_generate_unique_arrays(xp, xps):
    """Generates unique arrays."""
    skip_on_missing_unique_values(xp)
    assert_all_examples(
        xps.arrays(xp.int8, st.integers(0, 20), unique=True),
        lambda x: xp.unique_values(x).size == x.size,
    )


def test_cannot_draw_unique_arrays_with_too_small_elements(xp, xps):
    """Unique strategy with elements strategy range smaller than its size raises
    helpful error."""
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(
            xps.arrays(xp.int8, 10, elements=st.integers(0, 5), unique=True)
        )


def test_cannot_fill_arrays_with_non_castable_value(xp, xps):
    """Strategy with fill not castable to dtype raises helpful error."""
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(
            xps.arrays(xp.int8, 10, fill=st.just("not a castable value"))
        )


def test_generate_unique_arrays_with_high_collision_elements(xp, xps):
    """Generates unique arrays with just elements of 0.0 and NaN fill."""

    @given(
        xps.arrays(
            dtype=xp.float32,
            shape=st.integers(0, 20),
            elements=st.just(0.0),
            fill=st.just(xp.nan),
            unique=True,
        )
    )
    def test(x):
        zero_mask = x == 0.0
        assert xp.sum(xp.astype(zero_mask, xp.uint8)) <= 1

    test()


def test_generate_unique_arrays_using_all_elements(xp, xps):
    """Unique strategy with elements strategy range equal to its size will only
    generate arrays with one of each possible element."""
    skip_on_missing_unique_values(xp)
    assert_all_examples(
        xps.arrays(xp.int8, (4,), elements=st.integers(0, 3), unique=True),
        lambda x: xp.unique_values(x).size == x.size,
    )


def test_may_fill_unique_arrays_with_nan(xp, xps):
    """Unique strategy with NaN fill can generate arrays holding NaNs."""
    find_any(
        xps.arrays(
            dtype=xp.float32,
            shape=10,
            elements={"allow_nan": False},
            unique=True,
            fill=st.just(xp.nan),
        ),
        lambda x: xp.any(xp.isnan(x)),
    )


def test_may_not_fill_unique_array_with_non_nan(xp, xps):
    """Unique strategy with just fill elements of 0.0 raises helpful error."""
    strat = xps.arrays(
        dtype=xp.float32,
        shape=10,
        elements={"allow_nan": False},
        unique=True,
        fill=st.just(0.0),
    )
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(strat)


def test_floating_point_array():
    import warnings

    from hypothesis.extra.array_api import make_strategies_namespace

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import numpy.array_api as nxp
    except ModuleNotFoundError:
        import numpy as nxp
    xps = make_strategies_namespace(nxp)
    dtypes = xps.floating_dtypes() | xps.complex_dtypes()

    strat = xps.arrays(dtype=dtypes, shape=10)

    check_can_generate_examples(strat)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"elements": st.just(300)},
        {"elements": st.nothing(), "fill": st.just(300)},
    ],
)
def test_may_not_use_overflowing_integers(xp, xps, kwargs):
    """Strategy with elements strategy range outside the dtype's bounds raises
    helpful error."""
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(xps.arrays(dtype=xp.int8, shape=1, **kwargs))


@pytest.mark.parametrize("fill", [False, True])
@pytest.mark.parametrize(
    "dtype, strat",
    [
        ("float32", st.floats(min_value=10**40, allow_infinity=False)),
        ("float64", st.floats(min_value=10**40, allow_infinity=False)),
        pytest.param(
            "complex64",
            st.complex_numbers(min_magnitude=10**300, allow_infinity=False),
            marks=pytest.mark.xp_min_version(MIN_VER_FOR_COMPLEX),
        ),
    ],
)
def test_may_not_use_unrepresentable_elements(xp, xps, fill, dtype, strat):
    """Strategy with elements not representable by the dtype raises helpful error."""
    if fill:
        kw = {"elements": st.nothing(), "fill": strat}
    else:
        kw = {"elements": strat}
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(xps.arrays(dtype=dtype, shape=1, **kw))


def test_floats_can_be_constrained(xp, xps):
    """Strategy with float dtype and specified elements strategy range
    (inclusive) generates arrays with elements inside said range."""
    assert_all_examples(
        xps.arrays(
            dtype=xp.float32, shape=10, elements={"min_value": 0, "max_value": 1}
        ),
        lambda x: xp.all(x >= 0) and xp.all(x <= 1),
    )


def test_floats_can_be_constrained_excluding_endpoints(xp, xps):
    """Strategy with float dtype and specified elements strategy range
    (exclusive) generates arrays with elements inside said range."""
    assert_all_examples(
        xps.arrays(
            dtype=xp.float32,
            shape=10,
            elements={
                "min_value": 0,
                "max_value": 1,
                "exclude_min": True,
                "exclude_max": True,
            },
        ),
        lambda x: xp.all(x > 0) and xp.all(x < 1),
    )


def test_is_still_unique_with_nan_fill(xp, xps):
    """Unique strategy with NaN fill generates unique arrays."""
    skip_on_missing_unique_values(xp)
    xfail_on_indistinct_nans(xp)
    assert_all_examples(
        xps.arrays(
            dtype=xp.float32,
            elements={"allow_nan": False},
            shape=10,
            unique=True,
            fill=st.just(xp.nan),
        ),
        lambda x: xp.unique_values(x).size == x.size,
    )


def test_unique_array_with_fill_can_use_all_elements(xp, xps):
    """Unique strategy with elements range equivalent to its size and NaN fill
    can generate arrays with all possible values."""
    skip_on_missing_unique_values(xp)
    xfail_on_indistinct_nans(xp)
    find_any(
        xps.arrays(
            dtype=xp.float32,
            shape=10,
            unique=True,
            elements=st.integers(1, 9),
            fill=st.just(xp.nan),
        ),
        lambda x: xp.unique_values(x).size == x.size,
    )


def test_generate_unique_arrays_without_fill(xp, xps):
    """Generate arrays from unique strategy with no fill.

    Covers the collision-related branches for fully dense unique arrays.
    Choosing 25 of 256 possible values means we're almost certain to see
    collisions thanks to the birthday paradox, but finding unique values should
    still be easy.
    """
    skip_on_missing_unique_values(xp)
    assert_all_examples(
        xps.arrays(dtype=xp.uint8, shape=25, unique=True, fill=st.nothing()),
        lambda x: xp.unique_values(x).size == x.size,
    )


def test_efficiently_generate_unique_arrays_using_all_elements(xp, xps):
    """Unique strategy with elements strategy range equivalent to its size
    generates arrays with all possible values. Generation is not too slow.

    Avoids the birthday paradox with UniqueSampledListStrategy.
    """
    skip_on_missing_unique_values(xp)
    assert_all_examples(
        xps.arrays(dtype=xp.int8, shape=255, unique=True),
        lambda x: xp.unique_values(x).size == x.size,
    )


@given(st.data(), st.integers(-100, 100), st.integers(1, 100))
def test_array_element_rewriting(xp, xps, data, start, size):
    """Unique strategy generates arrays with expected elements."""
    x = data.draw(
        xps.arrays(
            dtype=xp.int64,
            shape=size,
            elements=st.integers(start, start + size - 1),
            unique=True,
        )
    )
    x_set_expect = xp.arange(start, start + size, dtype=xp.int64)
    x_set = xp.sort(xp.unique_values(x))
    assert xp.all(x_set == x_set_expect)


def test_generate_0d_arrays_with_no_fill(xp, xps):
    """Generate arrays with zero-dimensions and no fill."""
    assert_all_examples(
        xps.arrays(xp.bool, (), fill=st.nothing()),
        lambda x: x.dtype == xp.bool and x.shape == (),
    )


@pytest.mark.parametrize("dtype", ["float32", "float64"])
@pytest.mark.parametrize("low", [-2.0, -1.0, 0.0, 1.0])
@given(st.data())
def test_excluded_min_in_float_arrays(xp, xps, dtype, low, data):
    """Strategy with elements strategy excluding min does not generate arrays
    with elements less or equal to said min."""
    strat = xps.arrays(
        dtype=dtype,
        shape=(),
        elements={
            "min_value": low,
            "max_value": low + 1,
            "exclude_min": True,
        },
    )
    x = data.draw(strat, label="array")
    assert xp.all(x > low)


@st.composite
def distinct_int64_integers(draw):
    used = draw(st.shared(st.builds(set), key="distinct_int64_integers.used"))
    i = draw(st.integers(-(2**63), 2**63 - 1).filter(lambda x: x not in used))
    used.add(i)
    return i


def test_does_not_reuse_distinct_integers(xp, xps):
    """Strategy with distinct integer elements strategy generates arrays with
    distinct values."""
    skip_on_missing_unique_values(xp)
    assert_all_examples(
        xps.arrays(xp.int64, 10, elements=distinct_int64_integers()),
        lambda x: xp.unique_values(x).size == x.size,
    )


def test_may_reuse_distinct_integers_if_asked(xp, xps):
    """Strategy with shared elements and fill strategies of distinct integers
    may generate arrays with non-distinct values."""
    skip_on_missing_unique_values(xp)
    find_any(
        xps.arrays(
            xp.int64,
            10,
            elements=distinct_int64_integers(),
            fill=distinct_int64_integers(),
        ),
        lambda x: xp.unique_values(x).size < x.size,
    )


def test_subnormal_elements_validation(xp, xps):
    """Strategy with subnormal elements strategy is correctly validated.

    For FTZ builds of array modules, a helpful error should raise. Conversely,
    for builds of array modules which support subnormals, the strategy should
    generate arrays without raising.
    """
    elements = {
        "min_value": 0.0,
        "max_value": width_smallest_normals[32],
        "exclude_min": True,
        "exclude_max": True,
        "allow_subnormal": True,
    }
    strat = xps.arrays(xp.float32, 10, elements=elements)
    if flushes_to_zero(xp, width=32):
        with pytest.raises(InvalidArgument, match="Generated subnormal float"):
            check_can_generate_examples(strat)
    else:
        check_can_generate_examples(strat)
