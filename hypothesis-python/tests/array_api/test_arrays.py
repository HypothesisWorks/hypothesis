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

from hypothesis import assume, given, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.extra.array_api import DTYPE_NAMES, NUMERIC_NAMES

from tests.array_api.common import COMPLIANT_XP, xp, xps
from tests.common.debug import find_any, minimal
from tests.common.utils import fails_with, flaky

pytestmark = [pytest.mark.mockable_xp]


def assert_array_namespace(x):
    """Check array has __array_namespace__() and it returns the correct module.

    This check is skipped if a mock array module is being used.
    """
    if COMPLIANT_XP:
        assert x.__array_namespace__() is xp


@given(xps.scalar_dtypes(), st.data())
def test_draw_arrays_from_dtype(dtype, data):
    """Draw arrays from dtypes."""
    x = data.draw(xps.arrays(dtype, ()))
    assert x.dtype == dtype
    assert_array_namespace(x)


@given(st.sampled_from(DTYPE_NAMES), st.data())
def test_draw_arrays_from_scalar_names(name, data):
    """Draw arrays from dtype names."""
    x = data.draw(xps.arrays(name, ()))
    assert x.dtype == getattr(xp, name)
    assert_array_namespace(x)


@given(xps.array_shapes(), st.data())
def test_draw_arrays_from_shapes(shape, data):
    """Draw arrays from shapes."""
    x = data.draw(xps.arrays(xp.int8, shape))
    assert x.ndim == len(shape)
    assert x.shape == shape
    assert_array_namespace(x)


@given(st.integers(0, 10), st.data())
def test_draw_arrays_from_int_shapes(size, data):
    """Draw arrays from integers as shapes."""
    x = data.draw(xps.arrays(xp.int8, size))
    assert x.shape == (size,)
    assert_array_namespace(x)


@pytest.mark.parametrize(
    "strat",
    [
        xps.scalar_dtypes(),
        xps.boolean_dtypes(),
        xps.integer_dtypes(),
        xps.unsigned_integer_dtypes(),
        xps.floating_dtypes(),
    ],
)
@given(st.data())
def test_draw_arrays_from_dtype_strategies(strat, data):
    """Draw arrays from dtype strategies."""
    x = data.draw(xps.arrays(strat, ()))
    assert_array_namespace(x)


@given(st.lists(st.sampled_from(DTYPE_NAMES), min_size=1, unique=True), st.data())
def test_draw_arrays_from_dtype_name_strategies(names, data):
    """Draw arrays from dtype name strategies."""
    names_strategy = st.sampled_from(names)
    x = data.draw(xps.arrays(names_strategy, ()))
    assert_array_namespace(x)


@given(xps.arrays(xp.int8, xps.array_shapes()))
def test_generate_arrays_from_shapes_strategy(x):
    """Generate arrays from shapes strategy."""
    assert_array_namespace(x)


@given(xps.arrays(xp.int8, st.integers(0, 100)))
def test_generate_arrays_from_integers_strategy_as_shape(x):
    """Generate arrays from integers strategy as shapes strategy."""
    assert_array_namespace(x)


@given(xps.arrays(xp.int8, ()))
def test_generate_arrays_from_zero_dimensions(x):
    """Generate arrays from empty shape."""
    assert x.shape == ()
    assert_array_namespace(x)


@given(xps.arrays(xp.int8, (1, 0, 1)))
def test_handle_zero_dimensions(x):
    """Generate arrays from empty shape."""
    assert x.shape == (1, 0, 1)
    assert_array_namespace(x)


@given(xps.arrays(xp.uint32, (5, 5)))
def test_generate_arrays_from_unsigned_ints(x):
    """Generate arrays from unsigned integer dtype."""
    assert xp.all(x >= 0)
    assert_array_namespace(x)


def test_minimize_arrays_with_default_dtype_shape_strategies():
    """Strategy with default scalar_dtypes and array_shapes strategies minimize
    to a boolean 1-dimensional array of size 1."""
    smallest = minimal(xps.arrays(xps.scalar_dtypes(), xps.array_shapes()))
    assert smallest.shape == (1,)
    assert smallest.dtype == xp.bool
    assert not xp.any(smallest)


def test_minimize_arrays_with_0d_shape_strategy():
    """Strategy with shape strategy that can generate empty tuples minimizes to
    0d arrays."""
    smallest = minimal(xps.arrays(xp.int8, xps.array_shapes(min_dims=0)))
    assert smallest.shape == ()


@pytest.mark.parametrize("dtype", NUMERIC_NAMES)
def test_minimizes_numeric_arrays(dtype):
    """Strategies with numeric dtypes minimize to zero-filled arrays."""
    smallest = minimal(xps.arrays(dtype, (2, 2)))
    assert xp.all(smallest == 0)


def test_minimize_large_uint_arrays():
    """Strategy with uint dtype and largely sized shape minimizes to a good
    example."""
    smallest = minimal(
        xps.arrays(xp.uint8, 100),
        lambda x: xp.any(x) and not xp.all(x),
        timeout_after=60,
    )
    assert xp.all(xp.logical_or(smallest == 0, smallest == 1))
    if hasattr(xp, "nonzero"):
        idx = xp.nonzero(smallest)[0]
        assert idx.size in (1, smallest.size - 1)
    else:
        pytest.skip()


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@flaky(max_runs=50, min_passes=1)
def test_minimize_float_arrays():
    """Strategy with float dtype minimizes to a good example.

    We filter runtime warnings and expect flaky array generation for
    specifically NumPy - this behaviour may not be required when testing
    with other array libraries.
    """
    smallest = minimal(xps.arrays(xp.float32, 50), lambda x: xp.sum(x) >= 1.0)
    assert xp.sum(smallest) in (1, 50)


def test_minimizes_to_fill():
    """Strategy with single fill value minimizes to arrays only containing said
    fill value."""
    smallest = minimal(xps.arrays(xp.float32, 10, fill=st.just(3.0)))
    assert xp.all(smallest == 3.0)


def count_unique(x):
    """Returns the number of unique elements.
    NaN values are treated as unique to each other.

    The Array API doesn't specify how ``unique()`` should behave for Nan values,
    so this method provides consistent behaviour.
    """
    n_unique = 0

    nan_index = xp.isnan(x)
    for isnan, count in zip(*xp.unique(nan_index, return_counts=True)):
        if isnan:
            n_unique += count
            break

    # TODO: The Array API makes boolean indexing optional, so in the future this
    # will need to be reworked if we want to test libraries other than NumPy.
    # If not possible, errors should be caught and the test skipped.
    filtered_x = x[~nan_index]
    unique_x = xp.unique(filtered_x)
    n_unique += unique_x.size

    return n_unique


@given(
    xps.arrays(
        dtype=xp.float32,
        elements=st.just(xp.nan),
        shape=xps.array_shapes(),
    )
)
def test_count_unique(x):
    """Utility counts unique elements of arrays generated by unique strategy."""
    if hasattr(xp, "unique"):
        assert count_unique(x) == x.size
    else:
        pytest.skip()


@given(xps.arrays(xp.int8, st.integers(0, 20), unique=True))
def test_generate_unique_arrays(x):
    """Generates unique arrays."""
    if hasattr(xp, "unique"):
        assert count_unique(x) == x.size
    else:
        pytest.skip()


def test_cannot_draw_unique_arrays_with_too_small_elements():
    """Unique strategy with elements strategy range smaller than its size raises
    helpful error."""
    strat = xps.arrays(xp.int8, 10, elements=st.integers(0, 5), unique=True)
    with pytest.raises(InvalidArgument):
        strat.example()


def test_cannot_fill_arrays_with_non_castable_value():
    """Strategy with fill not castable to dtype raises helpful error."""
    strat = xps.arrays(xp.int8, 10, fill=st.just("not a castable value"))
    with pytest.raises(InvalidArgument):
        strat.example()


@given(
    xps.arrays(
        dtype=xp.float32,
        shape=st.integers(0, 20),
        elements=st.just(0.0),
        fill=st.just(xp.nan),
        unique=True,
    )
)
def test_generate_unique_arrays_with_high_collision_elements(x):
    """Generates unique arrays with just elements of 0.0 and NaN fill."""
    assert xp.sum(x == 0.0) <= 1


@given(xps.arrays(xp.int8, (4,), elements=st.integers(0, 3), unique=True))
def test_generate_unique_arrays_using_all_elements(x):
    """Unique strategy with elements strategy range equal to its size will only
    generate arrays with one of each possible element."""
    if hasattr(xp, "unique"):
        assert count_unique(x) == x.size
    else:
        pytest.skip()


def test_may_fill_unique_arrays_with_nan():
    """Unique strategy with NaN fill can generate arrays holding NaNs."""
    find_any(
        xps.arrays(
            dtype=xp.float32,
            shape=10,
            elements=st.floats(allow_nan=False),
            unique=True,
            fill=st.just(xp.nan),
        ),
        lambda x: xp.any(xp.isnan(x)),
    )


@fails_with(InvalidArgument)
@given(
    xps.arrays(
        dtype=xp.float32,
        shape=10,
        elements=st.floats(allow_nan=False),
        unique=True,
        fill=st.just(0.0),
    )
)
def test_may_not_fill_unique_array_with_non_nan(_):
    """Unique strategy with just fill elements of 0.0 raises helpful error."""


@pytest.mark.parametrize(
    "kwargs",
    [
        {"elements": st.just(300)},
        {"elements": st.nothing(), "fill": st.just(300)},
    ],
)
@fails_with(InvalidArgument)
@given(st.data())
def test_may_not_use_overflowing_integers(kwargs, data):
    """Strategy with elements strategy range outside the dtype's bounds raises
    helpful error."""
    strat = xps.arrays(dtype=xp.int8, shape=1, **kwargs)
    data.draw(strat)


@pytest.mark.parametrize("fill", [False, True])
@pytest.mark.parametrize(
    "dtype, strat",
    [
        (xp.float32, st.floats(min_value=10 ** 40, allow_infinity=False)),
        (xp.float64, st.floats(min_value=10 ** 40, allow_infinity=False)),
    ],
)
@fails_with(InvalidArgument)
@given(st.data())
def test_may_not_use_unrepresentable_elements(fill, dtype, strat, data):
    """Strategy with elements not representable by the dtype raises helpful error."""
    if fill:
        kw = {"elements": st.nothing(), "fill": strat}
    else:
        kw = {"elements": strat}
    strat = xps.arrays(dtype=dtype, shape=1, **kw)
    data.draw(strat)


@given(
    xps.arrays(dtype=xp.float32, shape=10, elements={"min_value": 0, "max_value": 1})
)
def test_floats_can_be_constrained(x):
    """Strategy with float dtype and specified elements strategy range
    (inclusive) generates arrays with elements inside said range."""
    assert xp.all(x >= 0)
    assert xp.all(x <= 1)


@given(
    xps.arrays(
        dtype=xp.float32,
        shape=10,
        elements={
            "min_value": 0,
            "max_value": 1,
            "exclude_min": True,
            "exclude_max": True,
        },
    )
)
def test_floats_can_be_constrained_excluding_endpoints(x):
    """Strategy with float dtype and specified elements strategy range
    (exclusive) generates arrays with elements inside said range."""
    assert xp.all(x > 0)
    assert xp.all(x < 1)


@given(
    xps.arrays(
        dtype=xp.float32,
        elements=st.floats(allow_nan=False, width=32),
        shape=10,
        unique=True,
        fill=st.just(xp.nan),
    )
)
def test_is_still_unique_with_nan_fill(x):
    """Unique strategy with NaN fill generates unique arrays."""
    if hasattr(xp, "unique"):
        assert count_unique(x) == x.size
    else:
        pytest.skip()


@given(
    xps.arrays(
        dtype=xp.float32,
        shape=10,
        unique=True,
        elements=st.integers(1, 9),
        fill=st.just(xp.nan),
    )
)
def test_unique_array_with_fill_can_use_all_elements(x):
    """Unique strategy with elements range equivalent to its size and NaN fill
    can generate arrays with all possible values."""
    if hasattr(xp, "unique"):
        assume(count_unique(x) == x.size)
    else:
        pytest.skip()


@given(xps.arrays(dtype=xp.uint8, shape=25, unique=True, fill=st.nothing()))
def test_generate_unique_arrays_without_fill(x):
    """Generate arrays from unique strategy with no fill.

    Covers the collision-related branches for fully dense unique arrays.
    Choosing 25 of 256 possible values means we're almost certain to see
    colisions thanks to the birthday paradox, but finding unique values should
    still be easy.
    """
    if hasattr(xp, "unique"):
        assume(count_unique(x) == x.size)
    else:
        pytest.skip()


@given(xps.arrays(dtype=xp.int8, shape=255, unique=True))
def test_efficiently_generate_unique_arrays_using_all_elements(x):
    """Unique strategy with elements strategy range equivalent to its size
    generates arrays with all possible values. Generation is not too slow.

    Avoids the birthday paradox with UniqueSampledListStrategy.
    """
    if hasattr(xp, "unique"):
        assert count_unique(x) == x.size
    else:
        pytest.skip()


@given(st.data(), st.integers(-100, 100), st.integers(1, 100))
def test_array_element_rewriting(data, start, size):
    """Unique strategy generates arrays with expected elements."""
    if hasattr(xp, "unique"):
        x = data.draw(
            xps.arrays(
                dtype=xp.int64,
                shape=size,
                elements=st.integers(start, start + size - 1),
                unique=True,
            )
        )
        x_set_expect = xp.linspace(start, start + size - 1, size, dtype=xp.int64)
        x_set = xp.sort(xp.unique(x))
        assert xp.all(x_set == x_set_expect)
    else:
        pytest.skip()


@given(xps.arrays(xp.bool, (), fill=st.nothing()))
def test_generate_0d_arrays_with_no_fill(x):
    """Generate arrays with zero-dimensions and no fill."""
    assert x.dtype == xp.bool
    assert x.shape == ()


@pytest.mark.parametrize("dtype", [xp.float32, xp.float64])
@pytest.mark.parametrize("low", [-2.0, -1.0, 0.0, 1.0])
@given(st.data())
def test_excluded_min_in_float_arrays(dtype, low, data):
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
def distinct_integers(draw):
    used = draw(st.shared(st.builds(set), key="distinct_integers.used"))
    i = draw(st.integers(0, 2 ** 64 - 1).filter(lambda x: x not in used))
    used.add(i)
    return i


@given(xps.arrays(xp.uint64, 10, elements=distinct_integers()))
def test_does_not_reuse_distinct_integers(x):
    """Strategy with distinct integer elements strategy generates arrays with
    distinct values."""
    if hasattr(xp, "unique"):
        assert count_unique(x) == x.size
    else:
        pytest.skip()


def test_may_reuse_distinct_integers_if_asked():
    """Strategy with shared elements and fill strategies of distinct integers
    may generate arrays with non-distinct values."""
    if hasattr(xp, "unique"):
        find_any(
            xps.arrays(
                xp.uint64, 10, elements=distinct_integers(), fill=distinct_integers()
            ),
            lambda x: count_unique(x) < x.size,
        )
    else:
        pytest.skip()
