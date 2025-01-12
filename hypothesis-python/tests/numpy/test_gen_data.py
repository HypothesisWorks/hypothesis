# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys
from functools import reduce
from itertools import zip_longest

import numpy as np
import pytest

from hypothesis import (
    HealthCheck,
    Phase,
    assume,
    given,
    note,
    settings,
    strategies as st,
    target,
)
from hypothesis.errors import InvalidArgument, UnsatisfiedAssumption
from hypothesis.extra import numpy as nps
from hypothesis.strategies._internal.lazy import unwrap_strategies

from tests.common.debug import check_can_generate_examples, find_any, minimal
from tests.common.utils import fails_with, flaky

ANY_SHAPE = nps.array_shapes(min_dims=0, max_dims=32, min_side=0, max_side=32)
ANY_NONZERO_SHAPE = nps.array_shapes(min_dims=0, max_dims=32, min_side=1, max_side=32)


@given(nps.arrays(float, ()))
def test_empty_dimensions_are_arrays(x):
    assert isinstance(x, np.ndarray)
    assert x.dtype.kind == "f"


@given(nps.arrays(float, (1, 0, 1)))
def test_can_handle_zero_dimensions(x):
    assert x.shape == (1, 0, 1)


@given(nps.arrays("uint32", (5, 5)))
def test_generates_unsigned_ints(x):
    assert (x >= 0).all()


@given(nps.arrays(int, (1,)))
def test_assert_fits_in_machine_size(x):
    pass


def test_generates_and_minimizes():
    assert (minimal(nps.arrays(float, (2, 2))) == np.zeros(shape=(2, 2))).all()


def test_can_minimize_large_arrays():
    x = minimal(nps.arrays("uint32", 100), lambda x: np.any(x) and not np.all(x))
    assert np.logical_or(x == 0, x == 1).all()
    assert np.count_nonzero(x) in (1, len(x) - 1)


@flaky(max_runs=50, min_passes=1)
def test_can_minimize_float_arrays():
    with np.errstate(over="ignore", invalid="ignore"):
        x = minimal(nps.arrays(float, 50), lambda t: np.nansum(t) >= 1.0)
        assert x.sum() in (1, 50)


class Foo:
    pass


foos = st.tuples().map(lambda _: Foo())


def test_can_create_arrays_of_composite_types():
    arr = minimal(nps.arrays(object, 100, elements=foos))
    for x in arr:
        assert isinstance(x, Foo)


@given(st.lists(st.integers()), st.data())
def test_can_create_zero_dim_arrays_of_lists(x, data):
    arr = data.draw(nps.arrays(object, (), elements=st.just(x)))
    assert arr.shape == ()
    assert arr.dtype == np.dtype(object)
    assert arr.item() == x


def test_can_create_arrays_of_tuples():
    arr = minimal(
        nps.arrays(object, 10, elements=st.tuples(st.integers(), st.integers())),
        lambda x: all(t0 != t1 for t0, t1 in x),
    )
    assert all(a in ((1, 0), (0, 1)) for a in arr)


@given(nps.arrays(object, (2, 2), elements=st.tuples(st.integers())))
def test_does_not_flatten_arrays_of_tuples(arr):
    assert isinstance(arr[0][0], tuple)


@given(
    nps.arrays(object, (2, 2), elements=st.lists(st.integers(), min_size=1, max_size=1))
)
def test_does_not_flatten_arrays_of_lists(arr):
    assert isinstance(arr[0][0], list)


@given(nps.array_shapes())
def test_can_generate_array_shapes(shape):
    assert isinstance(shape, tuple)
    assert all(isinstance(i, int) for i in shape)


@settings(deadline=None, max_examples=10)
@given(st.integers(0, 10), st.integers(0, 9), st.integers(0), st.integers(0))
def test_minimise_array_shapes(min_dims, dim_range, min_side, side_range):
    smallest = minimal(
        nps.array_shapes(
            min_dims=min_dims,
            max_dims=min_dims + dim_range,
            min_side=min_side,
            max_side=min_side + side_range,
        )
    )
    assert len(smallest) == min_dims
    assert all(k == min_side for k in smallest)


@pytest.mark.parametrize(
    "kwargs", [{"min_side": 100}, {"min_dims": 15}, {"min_dims": 32}]
)
def test_interesting_array_shapes_argument(kwargs):
    check_can_generate_examples(nps.array_shapes(**kwargs))


@given(nps.scalar_dtypes())
def test_can_generate_scalar_dtypes(dtype):
    assert isinstance(dtype, np.dtype)


@settings(max_examples=100)
@given(
    nps.nested_dtypes(
        subtype_strategy=st.one_of(
            nps.scalar_dtypes(), nps.byte_string_dtypes(), nps.unicode_string_dtypes()
        )
    )
)
def test_can_generate_compound_dtypes(dtype):
    assert isinstance(dtype, np.dtype)


@settings(max_examples=100)
@given(
    nps.nested_dtypes(
        subtype_strategy=st.one_of(
            nps.scalar_dtypes(), nps.byte_string_dtypes(), nps.unicode_string_dtypes()
        )
    ).flatmap(lambda dt: nps.arrays(dtype=dt, shape=1))
)
def test_can_generate_data_compound_dtypes(arr):
    # This is meant to catch the class of errors which prompted PR #2085
    assert isinstance(arr, np.ndarray)


@given(nps.nested_dtypes())
def test_np_dtype_is_idempotent(dtype):
    assert dtype == np.dtype(dtype)


def test_minimise_scalar_dtypes():
    assert minimal(nps.scalar_dtypes()) == np.dtype("bool")


def test_minimise_nested_types():
    assert minimal(nps.nested_dtypes()) == np.dtype("bool")


def test_minimise_array_strategy():
    smallest = minimal(
        nps.arrays(
            nps.nested_dtypes(max_itemsize=200),
            nps.array_shapes(max_dims=3, max_side=3),
        )
    )
    assert smallest.dtype == np.dtype("bool")
    assert not smallest.any()


@given(nps.array_dtypes(allow_subarrays=False))
def test_can_turn_off_subarrays(dt):
    for name in dt.names:
        assert dt.fields[name][0].shape == ()


def test_array_dtypes_may_have_field_titles():
    find_any(nps.array_dtypes(), lambda dt: len(dt.fields) > len(dt.names))


@pytest.mark.parametrize("byteorder", ["<", ">"])
@given(data=st.data())
def test_can_restrict_endianness(data, byteorder):
    dtype = data.draw(nps.integer_dtypes(endianness=byteorder, sizes=(16, 32, 64)))
    if byteorder == ("<" if sys.byteorder == "little" else ">"):
        assert dtype.byteorder == "="
    else:
        assert dtype.byteorder == byteorder


@given(nps.integer_dtypes(sizes=8))
def test_can_specify_size_as_an_int(dt):
    assert dt.itemsize == 1


@given(st.data())
def test_can_draw_arrays_from_scalars(data):
    dt = data.draw(nps.scalar_dtypes())
    result = data.draw(nps.arrays(dtype=dt, shape=()))
    assert isinstance(result, np.ndarray)
    assert result.dtype == dt


@given(st.data())
def test_can_cast_for_arrays(data):
    # Note: this only passes with castable datatypes, certain dtype
    # combinations will result in an error if numpy is not able to cast them.
    dt_elements = np.dtype(data.draw(st.sampled_from(["bool", "<i2", ">i2"])))
    dt_desired = np.dtype(
        data.draw(st.sampled_from(["<i2", ">i2", "float32", "float64"]))
    )
    result = data.draw(
        nps.arrays(
            dtype=dt_desired, elements=nps.from_dtype(dt_elements), shape=(1, 2, 3)
        )
    )
    assert isinstance(result, np.ndarray)
    assert result.dtype == dt_desired


@given(nps.arrays(dtype="int8", shape=st.integers(0, 20), unique=True))
def test_array_values_are_unique(arr):
    assert len(set(arr)) == len(arr)


def test_cannot_generate_unique_array_of_too_many_elements():
    strat = nps.arrays(dtype=int, elements=st.integers(0, 5), shape=10, unique=True)
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(strat)


@given(
    nps.arrays(
        elements=st.just(0.0),
        dtype=float,
        fill=st.just(np.nan),
        shape=st.integers(0, 20),
        unique=True,
    )
)
def test_array_values_are_unique_high_collision(arr):
    assert (arr == 0.0).sum() <= 1


@given(nps.arrays(dtype="int8", shape=(4,), elements=st.integers(0, 3), unique=True))
def test_generates_all_values_for_unique_array(arr):
    # Ensures that the "reject already-seen element" branch is covered
    assert len(set(arr)) == len(arr)


@given(nps.arrays(dtype="int8", shape=255, unique=True))
def test_efficiently_generates_all_unique_array(arr):
    # Avoids the birthday paradox with UniqueSampledListStrategy
    assert len(set(arr)) == len(arr)


@given(st.data(), st.integers(-100, 100), st.integers(1, 100))
def test_array_element_rewriting(data, start, size):
    arr = nps.arrays(
        dtype=np.dtype("int64"),
        shape=size,
        elements=st.integers(start, start + size - 1),
        unique=True,
    )
    assert set(data.draw(arr)) == set(range(start, start + size))


def test_may_fill_with_nan_when_unique_is_set():
    find_any(
        nps.arrays(
            dtype=float,
            elements=st.floats(allow_nan=False),
            shape=10,
            unique=True,
            fill=st.just(np.nan),
        ),
        lambda x: np.isnan(x).any(),
    )


@given(
    nps.arrays(
        dtype=float,
        elements=st.floats(allow_nan=False),
        shape=10,
        unique=True,
        fill=st.just(np.nan),
    )
)
def test_is_still_unique_with_nan_fill(xs):
    assert len(set(xs)) == len(xs)


@fails_with(InvalidArgument)
@given(
    nps.arrays(
        dtype=float,
        elements=st.floats(allow_nan=False),
        shape=10,
        unique=True,
        fill=st.just(0.0),
    )
)
def test_may_not_fill_with_non_nan_when_unique_is_set(arr):
    pass


@fails_with(InvalidArgument)
@given(nps.arrays(dtype="U", shape=10, unique=True, fill=st.just("")))
def test_may_not_fill_with_non_nan_when_unique_is_set_and_type_is_not_number(arr):
    pass


np_version = tuple(int(x) for x in np.__version__.split(".")[:2])


@pytest.mark.parametrize("fill", [False, True])
# Overflowing elements deprecated upstream in Numpy 1.24 :-)
@fails_with(
    InvalidArgument
    if np_version < (1, 24)
    else (DeprecationWarning if np_version < (2, 0) else OverflowError)
)
@given(st.data())
def test_overflowing_integers_are_deprecated(fill, data):
    kw = {"elements": st.just(300)}
    if fill:
        kw = {"elements": st.nothing(), "fill": kw["elements"]}
    arr = data.draw(nps.arrays(dtype="int8", shape=(1,), **kw))
    assert arr[0] == (300 % 256)


@pytest.mark.parametrize("fill", [False, True])
@pytest.mark.parametrize(
    "dtype,strat",
    [
        ("float16", st.floats(min_value=65520, allow_infinity=False)),
        ("float32", st.floats(min_value=10**40, allow_infinity=False)),
        (
            "complex64",
            st.complex_numbers(min_magnitude=10**300, allow_infinity=False),
        ),
        ("U1", st.text(min_size=2, max_size=2)),
        ("S1", st.binary(min_size=2, max_size=2)),
    ],
)
@fails_with(InvalidArgument)
@given(data=st.data())
def test_unrepresentable_elements_are_deprecated(fill, dtype, strat, data):
    if fill:
        kw = {"elements": st.nothing(), "fill": strat}
    else:
        kw = {"elements": strat}
    try:
        arr = data.draw(nps.arrays(dtype=dtype, shape=(1,), **kw))
    except RuntimeWarning:
        assert np_version >= (1, 24), "New overflow-on-cast detection"
        raise InvalidArgument("so the test passes") from None

    try:
        # This is a float or complex number, and has overflowed to infinity,
        # triggering our deprecation for overflow.
        assert np.isinf(arr[0])
    except TypeError:
        # We tried to call isinf on a string.  The string was generated at
        # length two, then truncated by the dtype of size 1 - deprecation
        # again.  If the first character was \0 it is now the empty string.
        assert len(arr[0]) <= 1


@given(nps.arrays(dtype="float16", shape=(1,)))
def test_inferred_floats_do_not_overflow(arr):
    pass


@given(nps.arrays(dtype="float16", shape=10, elements={"min_value": 0, "max_value": 1}))
def test_inferred_floats_can_be_constrained_at_low_width(arr):
    assert (arr >= 0).all()
    assert (arr <= 1).all()


@given(
    nps.arrays(
        dtype="float16",
        shape=10,
        elements={
            "min_value": 0,
            "max_value": 1,
            "exclude_min": True,
            "exclude_max": True,
        },
    )
)
def test_inferred_floats_can_be_constrained_at_low_width_excluding_endpoints(arr):
    assert (arr > 0).all()
    assert (arr < 1).all()


@given(
    nps.arrays(
        dtype="float16",
        shape=10,
        unique=True,
        elements=st.integers(1, 9),
        fill=st.just(np.nan),
    )
)
def test_unique_array_with_fill_can_use_all_elements(arr):
    assume(len(set(arr)) == arr.size)


@given(nps.arrays(dtype="uint8", shape=25, unique=True, fill=st.nothing()))
def test_unique_array_without_fill(arr):
    # This test covers the collision-related branches for fully dense unique arrays.
    # Choosing 25 of 256 possible elements means we're almost certain to see collisions
    # thanks to the 'birthday paradox', but finding unique elemennts is still easy.
    assume(len(set(arr)) == arr.size)


@given(ndim=st.integers(0, 5), data=st.data())
def test_mapped_positive_axes_are_unique(ndim, data):
    min_size = data.draw(st.integers(0, ndim), label="min_size")
    max_size = data.draw(st.integers(min_size, ndim), label="max_size")
    axes = data.draw(
        nps.valid_tuple_axes(ndim, min_size=min_size, max_size=max_size), label="axes"
    )
    assert len(set(axes)) == len({i if 0 < i else ndim + i for i in axes})


@given(ndim=st.integers(0, 5), data=st.data())
def test_length_bounds_are_satisfied(ndim, data):
    min_size = data.draw(st.integers(0, ndim), label="min_size")
    max_size = data.draw(st.integers(min_size, ndim), label="max_size")
    axes = data.draw(
        nps.valid_tuple_axes(ndim, min_size=min_size, max_size=max_size), label="axes"
    )
    assert min_size <= len(axes) <= max_size


@given(shape=nps.array_shapes(), data=st.data())
def test_axes_are_valid_inputs_to_sum(shape, data):
    x = np.zeros(shape, dtype="uint8")
    axes = data.draw(nps.valid_tuple_axes(ndim=len(shape)), label="axes")
    np.sum(x, axes)


@settings(deadline=None, max_examples=10)
@given(ndim=st.integers(0, 3), data=st.data())
def test_minimize_tuple_axes(ndim, data):
    min_size = data.draw(st.integers(0, ndim), label="min_size")
    max_size = data.draw(st.integers(min_size, ndim), label="max_size")
    smallest = minimal(nps.valid_tuple_axes(ndim, min_size=min_size, max_size=max_size))
    assert len(smallest) == min_size
    assert all(k > -1 for k in smallest)


@settings(deadline=None, max_examples=10)
@given(ndim=st.integers(0, 3), data=st.data())
def test_minimize_negative_tuple_axes(ndim, data):
    min_size = data.draw(st.integers(0, ndim), label="min_size")
    max_size = data.draw(st.integers(min_size, ndim), label="max_size")
    smallest = minimal(
        nps.valid_tuple_axes(ndim, min_size=min_size, max_size=max_size),
        lambda x: all(i < 0 for i in x),
    )
    assert len(smallest) == min_size


@given(nps.broadcastable_shapes((), min_side=0, max_side=0, min_dims=0, max_dims=0))
def test_broadcastable_empty_shape(shape):
    assert shape == ()


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(shape=ANY_SHAPE, data=st.data())
def test_broadcastable_shape_bounds_are_satisfied(shape, data):
    min_dims = data.draw(st.integers(0, 32), label="min_dims")
    max_dims = data.draw(st.none() | st.integers(min_dims, 32), label="max_dims")
    min_side = data.draw(st.integers(0, 3), label="min_side")
    max_side = data.draw(st.none() | st.integers(min_side, 6), label="max_side")
    try:
        bshape = data.draw(
            nps.broadcastable_shapes(
                shape,
                min_side=min_side,
                max_side=max_side,
                min_dims=min_dims,
                max_dims=max_dims,
            ),
            label="bshape",
        )
    except InvalidArgument:
        raise UnsatisfiedAssumption from None

    if max_dims is None:
        max_dims = max(len(shape), min_dims) + 2

    if max_side is None:
        max_side = max((*shape[::-1][:max_dims], min_side)) + 2

    assert isinstance(bshape, tuple)
    assert all(isinstance(s, int) for s in bshape)
    assert min_dims <= len(bshape) <= max_dims
    assert all(min_side <= s <= max_side for s in bshape)


@settings(deadline=None)
@given(num_shapes=st.integers(1, 4), base_shape=ANY_SHAPE, data=st.data())
def test_mutually_broadcastable_shape_bounds_are_satisfied(
    num_shapes, base_shape, data
):
    min_dims = data.draw(st.integers(0, 32), label="min_dims")
    max_dims = data.draw(
        st.one_of(st.none(), st.integers(min_dims, 32)), label="max_dims"
    )
    min_side = data.draw(st.integers(0, 3), label="min_side")
    max_side = data.draw(
        st.one_of(st.none(), st.integers(min_side, 6)), label="max_side"
    )
    try:
        shapes, result = data.draw(
            nps.mutually_broadcastable_shapes(
                num_shapes=num_shapes,
                base_shape=base_shape,
                min_side=min_side,
                max_side=max_side,
                min_dims=min_dims,
                max_dims=max_dims,
            ),
            label="shapes, result",
        )
    except InvalidArgument:
        raise UnsatisfiedAssumption from None

    if max_dims is None:
        max_dims = max(len(base_shape), min_dims) + 2

    if max_side is None:
        max_side = max((*base_shape[::-1][:max_dims], min_side)) + 2

    assert isinstance(shapes, tuple)
    assert isinstance(result, tuple)
    assert all(isinstance(s, int) for s in result)

    for bshape in shapes:
        assert isinstance(bshape, tuple)
        assert all(isinstance(s, int) for s in bshape)
        assert min_dims <= len(bshape) <= max_dims
        assert all(min_side <= s <= max_side for s in bshape)


def _draw_valid_bounds(data, shape, max_dims, *, permit_none=True):
    if max_dims == 0 or not shape:
        return 0, None

    smallest_side = min(shape[::-1][:max_dims])
    min_strat = (
        st.sampled_from([1, smallest_side])
        if smallest_side > 1
        else st.just(smallest_side)
    )
    min_side = data.draw(min_strat, label="min_side")
    largest_side = max(max(shape[::-1][:max_dims]), min_side)
    if permit_none:
        max_strat = st.one_of(st.none(), st.integers(largest_side, largest_side + 2))
    else:
        max_strat = st.integers(largest_side, largest_side + 2)
    max_side = data.draw(max_strat, label="max_side")
    return min_side, max_side


def _broadcast_two_shapes(shape_a: nps.Shape, shape_b: nps.Shape) -> nps.Shape:
    result = []
    for a, b in zip_longest(reversed(shape_a), reversed(shape_b), fillvalue=1):
        if a != b and (a != 1) and (b != 1):
            raise ValueError(
                f"shapes {shape_a!r} and {shape_b!r} are not broadcast-compatible"
            )
        result.append(a if a != 1 else b)
    return tuple(reversed(result))


def _broadcast_shapes(*shapes):
    """Returns the shape resulting from broadcasting the
    input shapes together.

    Raises ValueError if the shapes are not broadcast-compatible"""
    assert shapes, "Must pass >=1 shapes to broadcast"
    return reduce(_broadcast_two_shapes, shapes, ())


@settings(deadline=None, max_examples=500)
@given(
    shapes=st.lists(
        nps.array_shapes(min_dims=0, min_side=0, max_dims=4, max_side=4), min_size=1
    )
)
def test_broadcastable_shape_util(shapes):
    """Ensures that `_broadcast_shapes` raises when fed incompatible shapes,
    and ensures that it produces the true broadcasted shape"""
    if len(shapes) == 1:
        assert _broadcast_shapes(*shapes) == shapes[0]
        return

    arrs = [np.zeros(s, dtype=np.uint8) for s in shapes]

    try:
        broadcast_out = np.broadcast_arrays(*arrs)
    except ValueError:
        with pytest.raises(ValueError):
            _broadcast_shapes(*shapes)
        return
    broadcasted_shape = _broadcast_shapes(*shapes)

    assert broadcast_out[0].shape == broadcasted_shape


@settings(deadline=None, max_examples=200)
@given(shape=ANY_NONZERO_SHAPE, data=st.data())
def test_broadcastable_shape_has_good_default_values(shape, data):
    # This test ensures that default parameters can always produce broadcast-compatible shapes
    broadcastable_shape = data.draw(
        nps.broadcastable_shapes(shape), label="broadcastable_shapes"
    )
    # error if drawn shape for b is not broadcast-compatible
    _broadcast_shapes(shape, broadcastable_shape)


@settings(deadline=None, max_examples=200)
@given(base_shape=ANY_SHAPE, num_shapes=st.integers(1, 10), data=st.data())
def test_mutually_broadcastableshapes_has_good_default_values(
    num_shapes, base_shape, data
):
    # This test ensures that default parameters can always produce broadcast-compatible shapes
    shapes, result = data.draw(
        nps.mutually_broadcastable_shapes(num_shapes=num_shapes, base_shape=base_shape),
        label="shapes, result",
    )
    assert len(shapes) == num_shapes
    # raises if shapes are not mutually-compatible
    assert result == _broadcast_shapes(base_shape, *shapes)


@settings(deadline=None)
@given(min_dims=st.integers(0, 32), shape=ANY_SHAPE, data=st.data())
def test_broadcastable_shape_can_broadcast(min_dims, shape, data):
    max_dims = data.draw(st.none() | st.integers(min_dims, 32), label="max_dims")
    min_side, max_side = _draw_valid_bounds(data, shape, max_dims)
    broadcastable_shape = data.draw(
        nps.broadcastable_shapes(
            shape,
            min_side=min_side,
            max_side=max_side,
            min_dims=min_dims,
            max_dims=max_dims,
        ),
        label="broadcastable_shapes",
    )
    # error if drawn shape for b is not broadcast-compatible
    _broadcast_shapes(shape, broadcastable_shape)


@settings(deadline=None)
@given(
    num_shapes=st.integers(1, 10),
    min_dims=st.integers(0, 32),
    base_shape=ANY_SHAPE,
    data=st.data(),
)
def test_mutually_broadcastable_shape_can_broadcast(
    num_shapes, min_dims, base_shape, data
):
    max_dims = data.draw(st.none() | st.integers(min_dims, 32), label="max_dims")
    min_side, max_side = _draw_valid_bounds(data, base_shape, max_dims)
    shapes, result = data.draw(
        nps.mutually_broadcastable_shapes(
            num_shapes=num_shapes,
            base_shape=base_shape,
            min_side=min_side,
            max_side=max_side,
            min_dims=min_dims,
            max_dims=max_dims,
        ),
        label="shapes, result",
    )

    # error if drawn shapes are not mutually broadcast-compatible
    assert result == _broadcast_shapes(base_shape, *shapes)


@settings(deadline=None, max_examples=50)
@given(
    num_shapes=st.integers(1, 3),
    min_dims=st.integers(0, 5),
    base_shape=nps.array_shapes(min_dims=0, max_dims=3, min_side=0, max_side=5),
    data=st.data(),
)
def test_minimize_mutually_broadcastable_shape(num_shapes, min_dims, base_shape, data):
    # Ensure aligned dimensions of broadcastable shape minimizes to `(1,) * min_dims`
    max_dims = data.draw(st.none() | st.integers(min_dims, 5), label="max_dims")
    min_side, max_side = _draw_valid_bounds(
        data, base_shape, max_dims, permit_none=False
    )

    if num_shapes > 1:
        # shrinking gets a little bit hairy when we have empty axes
        # and multiple num_shapes
        assume(min_side > 0)

    smallest_shapes, result = minimal(
        nps.mutually_broadcastable_shapes(
            num_shapes=num_shapes,
            base_shape=base_shape,
            min_side=min_side,
            max_side=max_side,
            min_dims=min_dims,
            max_dims=max_dims,
        )
    )
    note(f"smallest_shapes: {smallest_shapes}")
    note(f"result: {result}")
    assert len(smallest_shapes) == num_shapes
    assert result == _broadcast_shapes(base_shape, *smallest_shapes)
    for smallest in smallest_shapes:
        n_leading = max(len(smallest) - len(base_shape), 0)
        n_aligned = max(len(smallest) - n_leading, 0)
        note(f"n_leading: {n_leading}")
        note(f"n_aligned: {n_aligned} {base_shape[-n_aligned:]}")
        expected = [min_side] * n_leading + [
            (min(1, i) if i != 1 else min_side) if min_side <= 1 <= max_side else i
            for i in (base_shape[-n_aligned:] if n_aligned else ())
        ]
        assert tuple(expected) == smallest


@settings(deadline=None)
@given(max_dims=st.integers(4, 6), data=st.data())
def test_broadcastable_shape_adjusts_max_dim_with_explicit_bounds(max_dims, data):
    # Ensures that `broadcastable_shapes` limits itself to satisfiable dimensions
    # Broadcastable values can only be drawn for dims 0-3 for these shapes
    shape = data.draw(st.sampled_from([(5, 3, 2, 1), (0, 3, 2, 1)]), label="shape")
    broadcastable_shape = data.draw(
        nps.broadcastable_shapes(
            shape, min_side=2, max_side=3, min_dims=3, max_dims=max_dims
        ),
        label="broadcastable_shapes",
    )
    assert len(broadcastable_shape) == 3
    # error if drawn shape for b is not broadcast-compatible
    _broadcast_shapes(shape, broadcastable_shape)


@settings(deadline=None)
@given(
    max_side=st.sampled_from([3, None]),
    min_dims=st.integers(0, 4),
    num_shapes=st.integers(1, 3),
    data=st.data(),
)
def test_mutually_broadcastable_shape_adjusts_max_dim_with_default_bounds(
    max_side, min_dims, num_shapes, data
):
    # Ensures that `mutually_broadcastable_shapes` limits itself to satisfiable dimensions
    # when a default `max_dims` is derived.
    base_shape = data.draw(
        st.sampled_from([(5, 3, 2, 1), (0, 3, 2, 1)]), label="base_shape"
    )

    try:
        shapes, result = data.draw(
            nps.mutually_broadcastable_shapes(
                num_shapes=num_shapes,
                base_shape=base_shape,
                min_side=2,
                max_side=max_side,
                min_dims=min_dims,
            ),
            label="shapes, result",
        )
    except InvalidArgument:
        # There is no satisfiable `max_dims` for us to tune
        assert min_dims == 4
        assert max_side == 3 or base_shape[0] == 0
        return

    if max_side == 3 or base_shape[0] == 0:
        assert all(len(s) <= 3 for s in shapes)
    elif min_dims == 4:
        assert all(4 <= len(s) for s in shapes)

    # error if drawn shape for b is not broadcast-compatible
    assert len(shapes) == num_shapes
    assert result == _broadcast_shapes(base_shape, *shapes)


@settings(deadline=None, max_examples=10)
@given(min_dims=st.integers(0, 32), min_side=st.integers(2, 3), data=st.data())
def test_broadcastable_shape_shrinking_with_singleton_out_of_bounds(
    min_dims, min_side, data
):
    max_dims = data.draw(st.none() | st.integers(min_dims, 32), label="max_dims")
    max_side = data.draw(st.none() | st.integers(min_side, 6), label="max_side")
    shape = data.draw(st.integers(1, 4).map(lambda n: n * (1,)), label="shape")
    smallest = minimal(
        nps.broadcastable_shapes(
            shape,
            min_side=min_side,
            max_side=max_side,
            min_dims=min_dims,
            max_dims=max_dims,
        )
    )
    assert smallest == (min_side,) * min_dims


@settings(deadline=None, max_examples=50)
@given(
    num_shapes=st.integers(1, 4),
    min_dims=st.integers(0, 4),
    min_side=st.integers(2, 3),
    data=st.data(),
)
def test_mutually_broadcastable_shapes_shrinking_with_singleton_out_of_bounds(
    num_shapes, min_dims, min_side, data
):
    """Ensures that shapes minimize to `(min_side,) * min_dims` when singleton dimensions
    are disallowed."""
    max_dims = data.draw(st.none() | st.integers(min_dims, 4), label="max_dims")
    max_side = data.draw(
        st.one_of(st.none(), st.integers(min_side, 6)), label="max_side"
    )
    ndims = data.draw(st.integers(1, 4), label="ndim")
    base_shape = (1,) * ndims
    smallest_shapes, result = minimal(
        nps.mutually_broadcastable_shapes(
            num_shapes=num_shapes,
            base_shape=base_shape,
            min_side=min_side,
            max_side=max_side,
            min_dims=min_dims,
            max_dims=max_dims,
        )
    )
    note(f"(smallest_shapes, result): {(smallest_shapes, result)}")
    assert len(smallest_shapes) == num_shapes
    assert result == _broadcast_shapes(base_shape, *smallest_shapes)
    for smallest in smallest_shapes:
        assert smallest == (min_side,) * min_dims


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(
    num_shapes=st.integers(1, 4),
    min_dims=st.integers(1, 32),
    max_side=st.integers(1, 6),
    data=st.data(),
)
def test_mutually_broadcastable_shapes_only_singleton_is_valid(
    num_shapes, min_dims, max_side, data
):
    """Ensures that, when all aligned base-shape dim sizes are larger
    than ``max_side``, only singletons can be drawn"""
    max_dims = data.draw(st.integers(min_dims, 32), label="max_dims")
    base_shape = data.draw(
        nps.array_shapes(min_side=max_side + 1, min_dims=1), label="base_shape"
    )
    input_shapes, result = data.draw(
        nps.mutually_broadcastable_shapes(
            num_shapes=num_shapes,
            base_shape=base_shape,
            min_side=1,
            max_side=max_side,
            min_dims=min_dims,
            max_dims=max_dims,
        ),
        label="input_shapes, result",
    )

    assert len(input_shapes) == num_shapes
    assert result == _broadcast_shapes(base_shape, *input_shapes)
    for shape in input_shapes:
        assert all(i == 1 for i in shape[-len(base_shape) :])


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    shape=nps.array_shapes(min_dims=0, max_dims=3, min_side=0, max_side=5),
    max_dims=st.integers(0, 6),
    data=st.data(),
)
def test_broadcastable_shape_can_generate_arbitrary_ndims(shape, max_dims, data):
    # ensures that generates shapes can possess any length in [min_dims, max_dims]
    desired_ndim = data.draw(st.integers(0, max_dims), label="desired_ndim")
    min_dims = data.draw(
        st.one_of(st.none(), st.integers(0, desired_ndim)), label="min_dims"
    )
    # check default arg behavior too
    kwargs = {"min_dims": min_dims} if min_dims is not None else {}
    find_any(
        nps.broadcastable_shapes(shape, min_side=0, max_dims=max_dims, **kwargs),
        lambda x: len(x) == desired_ndim,
        settings(max_examples=10**6),
    )


@settings(deadline=None)
@given(
    num_shapes=st.integers(1, 3),
    base_shape=nps.array_shapes(min_dims=0, max_dims=3, min_side=0, max_side=5),
    max_dims=st.integers(0, 4),
    data=st.data(),
)
def test_mutually_broadcastable_shapes_can_generate_arbitrary_ndims(
    num_shapes, base_shape, max_dims, data
):
    # ensures that each generated shape can possess any length in [min_dims, max_dims]
    desired_ndims = data.draw(
        st.lists(st.integers(0, max_dims), min_size=num_shapes, max_size=num_shapes),
        label="desired_ndims",
    )
    min_dims = data.draw(
        st.one_of(st.none(), st.integers(0, min(desired_ndims))), label="min_dims"
    )
    # check default arg behavior too
    kwargs = {"min_dims": min_dims} if min_dims is not None else {}
    find_any(
        nps.mutually_broadcastable_shapes(
            num_shapes=num_shapes,
            base_shape=base_shape,
            min_side=0,
            max_dims=max_dims,
            **kwargs,
        ),
        lambda x: {len(s) for s in x.input_shapes} == set(desired_ndims),
        settings(max_examples=10**6),
    )


@settings(deadline=None, suppress_health_check=list(HealthCheck))
@given(
    base_shape=nps.array_shapes(min_dims=0, max_dims=3, min_side=0, max_side=2),
    max_dims=st.integers(1, 4),
)
def test_mutually_broadcastable_shapes_can_generate_interesting_singletons(
    base_shape, max_dims
):
    find_any(
        nps.mutually_broadcastable_shapes(
            num_shapes=2,
            base_shape=base_shape,
            min_side=0,
            max_dims=max_dims,
        ),
        lambda x: any(a != b for a, b in zip(*(s[::-1] for s in x.input_shapes))),  # type: ignore
    )


@pytest.mark.parametrize("base_shape", [(), (0,), (1,), (2,), (1, 2), (2, 1), (2, 2)])
def test_mutually_broadcastable_shapes_can_generate_mirrored_singletons(base_shape):
    def f(shapes: nps.BroadcastableShapes):
        x, y = shapes.input_shapes
        return x.count(1) == 1 and y.count(1) == 1 and x[::-1] == y

    find_any(
        nps.mutually_broadcastable_shapes(
            num_shapes=2,
            base_shape=base_shape,
            min_side=0,
            max_side=3,
            min_dims=2,
            max_dims=2,
        ),
        f,
    )


@settings(deadline=None)
@given(
    shape=nps.array_shapes(min_dims=1, min_side=1),
    dtype=st.one_of(nps.unsigned_integer_dtypes(), nps.integer_dtypes()),
    data=st.data(),
)
def test_advanced_integer_index_is_valid_with_default_result_shape(shape, dtype, data):
    index = data.draw(nps.integer_array_indices(shape, dtype=dtype))
    x = np.zeros(shape)
    out = x[index]  # raises if the index is invalid
    assert not np.shares_memory(x, out)  # advanced indexing should not return a view
    assert all(dtype == x.dtype for x in index)


@settings(deadline=None)
@given(
    shape=nps.array_shapes(min_dims=1, min_side=1),
    min_dims=st.integers(0, 3),
    min_side=st.integers(0, 3),
    dtype=st.one_of(nps.unsigned_integer_dtypes(), nps.integer_dtypes()),
    data=st.data(),
)
def test_advanced_integer_index_is_valid_and_satisfies_bounds(
    shape, min_dims, min_side, dtype, data
):
    max_side = data.draw(st.integers(min_side, min_side + 2), label="max_side")
    max_dims = data.draw(st.integers(min_dims, min_dims + 2), label="max_dims")
    index = data.draw(
        nps.integer_array_indices(
            shape,
            result_shape=nps.array_shapes(
                min_dims=min_dims,
                max_dims=max_dims,
                min_side=min_side,
                max_side=max_side,
            ),
            dtype=dtype,
        )
    )
    x = np.zeros(shape)
    out = x[index]  # raises if the index is invalid
    assert all(min_side <= s <= max_side for s in out.shape)
    assert min_dims <= out.ndim <= max_dims
    assert not np.shares_memory(x, out)  # advanced indexing should not return a view
    assert all(dtype == x.dtype for x in index)


@settings(deadline=None)
@given(
    shape=nps.array_shapes(min_dims=1, min_side=1),
    min_dims=st.integers(0, 3),
    min_side=st.integers(0, 3),
    dtype=st.sampled_from(["uint8", "int8"]),
    data=st.data(),
)
def test_advanced_integer_index_minimizes_as_documented(
    shape, min_dims, min_side, dtype, data
):
    max_side = data.draw(st.integers(min_side, min_side + 2), label="max_side")
    max_dims = data.draw(st.integers(min_dims, min_dims + 2), label="max_dims")
    result_shape = nps.array_shapes(
        min_dims=min_dims, max_dims=max_dims, min_side=min_side, max_side=max_side
    )
    smallest = minimal(
        nps.integer_array_indices(shape, result_shape=result_shape, dtype=dtype)
    )
    desired = len(shape) * (np.zeros(min_dims * [min_side]),)
    assert len(smallest) == len(desired)
    for s, d in zip(smallest, desired):
        np.testing.assert_array_equal(s, d)


@settings(deadline=None, max_examples=25)
@given(
    shape=nps.array_shapes(min_dims=1, max_dims=2, min_side=1, max_side=3),
    data=st.data(),
)
def test_advanced_integer_index_can_generate_any_pattern(shape, data):
    # ensures that generated index-arrays can be used to yield any pattern of elements from an array
    x = np.arange(np.prod(shape)).reshape(shape)

    target_array = data.draw(
        nps.arrays(
            shape=nps.array_shapes(min_dims=1, max_dims=2, min_side=1, max_side=2),
            elements=st.sampled_from(x.flatten()),
            dtype=x.dtype,
        ),
        label="target",
    )

    def index_selects_values_in_order(index):
        selected = x[index]
        target(len(set(selected.flatten())), label="unique indices")
        target(float(np.sum(target_array == selected)), label="elements correct")
        return np.all(target_array == selected)

    minimal(
        nps.integer_array_indices(shape, result_shape=st.just(target_array.shape)),
        index_selects_values_in_order,
        settings(max_examples=10**6, phases=[Phase.generate, Phase.target]),
    )


@pytest.mark.parametrize(
    "condition",
    [
        lambda ix: isinstance(ix, tuple) and Ellipsis in ix,
        lambda ix: isinstance(ix, tuple) and Ellipsis not in ix,
        lambda ix: isinstance(ix, tuple) and np.newaxis in ix,
        lambda ix: isinstance(ix, tuple) and np.newaxis not in ix,
        lambda ix: ix is Ellipsis,
        lambda ix: ix == np.newaxis,
    ],
)
def test_basic_indices_options(condition):
    indexers = nps.array_shapes(min_dims=0, max_dims=32).flatmap(
        lambda shape: nps.basic_indices(shape, allow_newaxis=True)
    )
    find_any(indexers, condition)


def test_basic_indices_can_generate_empty_tuple():
    find_any(nps.basic_indices(shape=(0, 0), allow_ellipsis=True), lambda ix: ix == ())


def test_basic_indices_can_generate_non_tuples():
    find_any(
        nps.basic_indices(shape=(0, 0), allow_ellipsis=True),
        lambda ix: not isinstance(ix, tuple),
    )


def test_basic_indices_can_generate_long_ellipsis():
    # Runs of slice(None) - such as [0,:,:,:,0] - can be replaced by e.g. [0,...,0]
    find_any(
        nps.basic_indices(shape=(1, 0, 0, 0, 1), allow_ellipsis=True),
        lambda ix: len(ix) == 3 and ix[1] == Ellipsis,
    )


@given(
    nps.basic_indices(shape=(0, 0, 0, 0, 0)).filter(
        lambda idx: isinstance(idx, tuple) and Ellipsis in idx
    )
)
def test_basic_indices_replaces_whole_axis_slices_with_ellipsis(idx):
    # `slice(None)` (aka `:`) is the only valid index for an axis of size
    # zero, so if all dimensions are 0 then a `...` will replace all the
    # slices because we generate `...` for entire contiguous runs of `:`
    assert slice(None) not in idx


def test_basic_indices_can_generate_indices_not_covering_all_dims():
    # These "flat indices" are skippable in the underlying BasicIndexStrategy,
    # so we ensure we're definitely generating them for nps.basic_indices().
    find_any(
        nps.basic_indices(shape=(3, 3, 3)),
        lambda ix: (
            (not isinstance(ix, tuple) and ix != Ellipsis)
            or (isinstance(ix, tuple) and Ellipsis not in ix and len(ix) < 3)
        ),
        settings=settings(max_examples=5_000),
    )


@given(
    shape=nps.array_shapes(min_dims=0, max_side=4)
    | nps.array_shapes(min_dims=0, min_side=0, max_side=10),
    allow_newaxis=st.booleans(),
    allow_ellipsis=st.booleans(),
    data=st.data(),
)
def test_basic_indices_generate_valid_indexers(
    shape, allow_newaxis, allow_ellipsis, data
):
    min_dims = data.draw(
        st.integers(0, 5 if allow_newaxis else len(shape)), label="min_dims"
    )
    max_dims = data.draw(
        st.none() | st.integers(min_dims, 32 if allow_newaxis else len(shape)),
        label="max_dims",
    )
    indexer = data.draw(
        nps.basic_indices(
            shape,
            min_dims=min_dims,
            max_dims=max_dims,
            allow_ellipsis=allow_ellipsis,
            allow_newaxis=allow_newaxis,
        ),
        label="indexer",
    )

    # Check that disallowed things are indeed absent
    if not allow_newaxis:
        if isinstance(indexer, tuple):
            assert 0 <= len(indexer) <= len(shape) + int(allow_ellipsis)
        else:
            assert 1 <= len(shape) + int(allow_ellipsis)
        assert np.newaxis not in shape
    if not allow_ellipsis:
        assert Ellipsis not in shape

    if 0 in shape:
        # If there's a zero in the shape, the array will have no elements.
        array = np.zeros(shape)
        assert array.size == 0
    elif np.prod(shape) <= 10**5:
        # If it's small enough to instantiate, do so with distinct elements.
        array = np.arange(np.prod(shape)).reshape(shape)
    else:
        # We can't cheat on this one, so just try another.
        assume(False)
    view = array[indexer]
    if not np.isscalar(view):
        assert min_dims <= view.ndim <= (32 if max_dims is None else max_dims)
        if view.size:
            assert np.shares_memory(view, array)


# addresses https://github.com/HypothesisWorks/hypothesis/issues/2582
@given(
    nps.arrays(
        shape=nps.array_shapes(min_dims=0, min_side=0), dtype=nps.floating_dtypes()
    )
)
def test_array_owns_memory(x: np.ndarray):
    assert x.base is None
    assert x[...].base is x


@given(st.data())
def test_no_recursion_in_multi_line_reprs_issue_3560(data):
    data.draw(nps.arrays(shape=(2,), dtype=float).map(lambda x: x))
    data.draw(
        nps.arrays(
            shape=(2,),
            dtype=float,
        ).map(lambda x: x)
    )


def test_infers_elements_and_fill():
    # Regression test for https://github.com/HypothesisWorks/hypothesis/issues/3900
    # We only infer a fill strategy if the elements_strategy has reusable values,
    # and the interaction of two performance fixes broke this.  Oops...
    s = unwrap_strategies(nps.arrays(dtype=np.uint32, shape=1))
    assert isinstance(s, nps.ArrayStrategy)
    assert repr(s.element_strategy) == f"integers(0, {2**32-1})"
    assert repr(s.fill) == f"integers(0, {2**32-1})"

    # But we _don't_ infer a fill if the elements strategy is non-reusable
    elems = st.builds(lambda x: x * 2, st.integers(1, 10)).map(np.uint32)
    assert not elems.has_reusable_values
    s = unwrap_strategies(nps.arrays(dtype=np.uint32, shape=1, elements=elems))
    assert s.fill.is_empty
