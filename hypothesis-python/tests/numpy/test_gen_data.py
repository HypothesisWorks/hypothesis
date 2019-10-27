# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import sys

import numpy as np
import pytest
import six

import hypothesis.extra.numpy as nps
import hypothesis.strategies as st
from hypothesis import HealthCheck, assume, given, note, settings
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import binary_type, text_type
from hypothesis.searchstrategy import SearchStrategy
from tests.common.debug import find_any, minimal
from tests.common.utils import checks_deprecated_behaviour, fails_with, flaky

STANDARD_TYPES = list(
    map(
        np.dtype,
        [
            u"int8",
            u"int16",
            u"int32",
            u"int64",
            u"uint8",
            u"uint16",
            u"uint32",
            u"uint64",
            u"float",
            u"float16",
            u"float32",
            u"float64",
            u"complex64",
            u"complex128",
            u"datetime64",
            u"timedelta64",
            bool,
            text_type,
            binary_type,
        ],
    )
)


@given(nps.nested_dtypes())
def test_strategies_for_standard_dtypes_have_reusable_values(dtype):
    assert nps.from_dtype(dtype).has_reusable_values


@pytest.mark.parametrize(u"t", STANDARD_TYPES)
def test_produces_instances(t):
    @given(nps.from_dtype(t))
    def test_is_t(x):
        assert isinstance(x, t.type)
        assert x.dtype.kind == t.kind

    test_is_t()


@given(nps.arrays(float, ()))
def test_empty_dimensions_are_arrays(x):
    assert isinstance(x, np.ndarray)
    assert x.dtype.kind == u"f"


@given(nps.arrays(float, (1, 0, 1)))
def test_can_handle_zero_dimensions(x):
    assert x.shape == (1, 0, 1)


@given(nps.arrays(u"uint32", (5, 5)))
def test_generates_unsigned_ints(x):
    assert (x >= 0).all()


@given(st.data())
def test_can_handle_long_shapes(data):
    """We can eliminate this test once we drop Py2 support."""
    for tt in six.integer_types:
        X = data.draw(nps.arrays(float, (tt(5),)))
        assert X.shape == (5,)
        X = data.draw(nps.arrays(float, (tt(5), tt(5))))
        assert X.shape == (5, 5)


@given(nps.arrays(int, (1,)))
def test_assert_fits_in_machine_size(x):
    pass


def test_generates_and_minimizes():
    assert (minimal(nps.arrays(float, (2, 2))) == np.zeros(shape=(2, 2))).all()


def test_can_minimize_large_arrays():
    x = minimal(
        nps.arrays(u"uint32", 100),
        lambda x: np.any(x) and not np.all(x),
        timeout_after=60,
    )
    assert np.logical_or(x == 0, x == 1).all()
    assert np.count_nonzero(x) in (1, len(x) - 1)


@flaky(max_runs=50, min_passes=1)
def test_can_minimize_float_arrays():
    x = minimal(nps.arrays(float, 50), lambda t: t.sum() >= 1.0)
    assert x.sum() in (1, 50)


class Foo(object):
    pass


foos = st.tuples().map(lambda _: Foo())


def test_can_create_arrays_of_composite_types():
    arr = minimal(nps.arrays(object, 100, foos))
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
        nps.arrays(object, 10, st.tuples(st.integers(), st.integers())),
        lambda x: all(t0 != t1 for t0, t1 in x),
    )
    assert all(a in ((1, 0), (0, 1)) for a in arr)


@given(nps.arrays(object, (2, 2), st.tuples(st.integers())))
def test_does_not_flatten_arrays_of_tuples(arr):
    assert isinstance(arr[0][0], tuple)


@given(nps.arrays(object, (2, 2), st.lists(st.integers(), min_size=1, max_size=1)))
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
            min_dims, min_dims + dim_range, min_side, min_side + side_range
        )
    )
    assert len(smallest) == min_dims and all(k == min_side for k in smallest)


@pytest.mark.parametrize(
    "kwargs", [dict(min_side=100), dict(min_dims=15), dict(min_dims=32)]
)
def test_interesting_array_shapes_argument(kwargs):
    nps.array_shapes(**kwargs).example()


@given(nps.scalar_dtypes())
def test_can_generate_scalar_dtypes(dtype):
    assert isinstance(dtype, np.dtype)


@given(
    nps.nested_dtypes(
        subtype_strategy=st.one_of(
            nps.scalar_dtypes(), nps.byte_string_dtypes(), nps.unicode_string_dtypes()
        )
    )
)
def test_can_generate_compound_dtypes(dtype):
    assert isinstance(dtype, np.dtype)


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


@given(nps.nested_dtypes(max_itemsize=400), st.data())
def test_infer_strategy_from_dtype(dtype, data):
    # Given a dtype
    assert isinstance(dtype, np.dtype)
    # We can infer a strategy
    strat = nps.from_dtype(dtype)
    assert isinstance(strat, SearchStrategy)
    # And use it to fill an array of that dtype
    data.draw(nps.arrays(dtype, 10, strat))


@given(nps.nested_dtypes())
def test_np_dtype_is_idempotent(dtype):
    assert dtype == np.dtype(dtype)


def test_minimise_scalar_dtypes():
    assert minimal(nps.scalar_dtypes()) == np.dtype(u"bool")


def test_minimise_nested_types():
    assert minimal(nps.nested_dtypes()) == np.dtype(u"bool")


def test_minimise_array_strategy():
    smallest = minimal(
        nps.arrays(
            nps.nested_dtypes(max_itemsize=200),
            nps.array_shapes(max_dims=3, max_side=3),
        )
    )
    assert smallest.dtype == np.dtype(u"bool") and not smallest.any()


@given(nps.array_dtypes(allow_subarrays=False))
def test_can_turn_off_subarrays(dt):
    for field, _ in dt.fields.values():
        assert field.shape == ()


@pytest.mark.parametrize("byteorder", ["<", ">"])
@given(data=st.data())
def test_can_restrict_endianness(data, byteorder):
    dtype = data.draw(nps.integer_dtypes(byteorder, sizes=(16, 32, 64)))
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
def test_can_cast_for_scalars(data):
    # Note: this only passes with castable datatypes, certain dtype
    # combinations will result in an error if numpy is not able to cast them.
    dt_elements = np.dtype(data.draw(st.sampled_from(["bool", "<i2", ">i2"])))
    dt_desired = np.dtype(
        data.draw(st.sampled_from(["<i2", ">i2", "float32", "float64"]))
    )
    result = data.draw(
        nps.arrays(dtype=dt_desired, elements=nps.from_dtype(dt_elements), shape=())
    )
    assert isinstance(result, np.ndarray)
    assert result.dtype == dt_desired


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


@given(st.data())
def test_unicode_string_dtypes_generate_unicode_strings(data):
    dt = data.draw(nps.unicode_string_dtypes())
    result = data.draw(nps.from_dtype(dt))
    assert isinstance(result, text_type)


@given(st.data())
def test_byte_string_dtypes_generate_unicode_strings(data):
    dt = data.draw(nps.byte_string_dtypes())
    result = data.draw(nps.from_dtype(dt))
    assert isinstance(result, binary_type)


@given(nps.arrays(dtype="int8", shape=st.integers(0, 20), unique=True))
def test_array_values_are_unique(arr):
    assert len(set(arr)) == len(arr)


@given(
    nps.arrays(
        elements=st.just(0.0),
        dtype=float,
        fill=st.just(float("nan")),
        shape=st.integers(0, 20),
        unique=True,
    )
)
def test_array_values_are_unique_high_collision(arr):
    assert (arr == 0.0).sum() <= 1


def test_may_fill_with_nan_when_unique_is_set():
    find_any(
        nps.arrays(
            dtype=float,
            elements=st.floats(allow_nan=False),
            shape=10,
            unique=True,
            fill=st.just(float("nan")),
        ),
        lambda x: np.isnan(x).any(),
    )


@given(
    nps.arrays(
        dtype=float,
        elements=st.floats(allow_nan=False),
        shape=10,
        unique=True,
        fill=st.just(float("nan")),
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
@given(nps.arrays(dtype="U", shape=10, unique=True, fill=st.just(u"")))
def test_may_not_fill_with_non_nan_when_unique_is_set_and_type_is_not_number(arr):
    pass


@given(
    st.data(),
    st.builds(
        "{}[{}]".format,
        st.sampled_from(("datetime64", "timedelta64")),
        st.sampled_from(nps.TIME_RESOLUTIONS),
    ).map(np.dtype),
)
def test_inferring_from_time_dtypes_gives_same_dtype(data, dtype):
    ex = data.draw(nps.from_dtype(dtype))
    assert dtype == ex.dtype


@given(st.data(), nps.byte_string_dtypes() | nps.unicode_string_dtypes())
def test_inferred_string_strategies_roundtrip(data, dtype):
    # Check that we never generate too-long or nul-terminated strings, which
    # cannot be read back out of an array.
    arr = np.zeros(shape=1, dtype=dtype)
    ex = data.draw(nps.from_dtype(arr.dtype))
    arr[0] = ex
    assert arr[0] == ex


@given(st.data(), nps.scalar_dtypes())
def test_all_inferred_scalar_strategies_roundtrip(data, dtype):
    # We only check scalars here, because record/compound/nested dtypes always
    # give an array of np.void objects.  We're interested in whether scalar
    # values are safe, not known type coercion.
    arr = np.zeros(shape=1, dtype=dtype)
    ex = data.draw(nps.from_dtype(arr.dtype))
    assume(ex == ex)  # If not, the roundtrip test *should* fail!  (eg NaN)
    arr[0] = ex
    assert arr[0] == ex


@pytest.mark.parametrize("fill", [False, True])
@checks_deprecated_behaviour
@given(st.data())
def test_overflowing_integers_are_deprecated(fill, data):
    kw = dict(elements=st.just(300))
    if fill:
        kw = dict(elements=st.nothing(), fill=kw["elements"])
    arr = data.draw(nps.arrays(dtype="int8", shape=(1,), **kw))
    assert arr[0] == (300 % 256)


@pytest.mark.parametrize("fill", [False, True])
@pytest.mark.parametrize(
    "dtype,strat",
    [
        ("float16", st.floats(min_value=65520, allow_infinity=False)),
        ("float32", st.floats(min_value=10 ** 40, allow_infinity=False)),
        ("complex64", st.complex_numbers(10 ** 300, allow_infinity=False)),
        ("U1", st.text(min_size=2, max_size=2)),
        ("S1", st.binary(min_size=2, max_size=2)),
    ],
)
@checks_deprecated_behaviour
@given(data=st.data())
def test_unrepresentable_elements_are_deprecated(fill, dtype, strat, data):
    if fill:
        kw = dict(elements=st.nothing(), fill=strat)
    else:
        kw = dict(elements=strat)
    arr = data.draw(nps.arrays(dtype=dtype, shape=(1,), **kw))
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
    # This test covers the collision-related branchs for fully dense unique arrays.
    # Choosing 25 of 256 possible elements means we're almost certain to see colisions
    # thanks to the 'birthday paradox', but finding unique elemennts is still easy.
    assume(len(set(arr)) == arr.size)


@given(ndim=st.integers(0, 5), data=st.data())
def test_mapped_positive_axes_are_unique(ndim, data):
    min_size = data.draw(st.integers(0, ndim), label="min_size")
    max_size = data.draw(st.integers(min_size, ndim), label="max_size")
    axes = data.draw(nps.valid_tuple_axes(ndim, min_size, max_size), label="axes")
    assert len(set(axes)) == len({i if 0 < i else ndim + i for i in axes})


@given(ndim=st.integers(0, 5), data=st.data())
def test_length_bounds_are_satisfied(ndim, data):
    min_size = data.draw(st.integers(0, ndim), label="min_size")
    max_size = data.draw(st.integers(min_size, ndim), label="max_size")
    axes = data.draw(nps.valid_tuple_axes(ndim, min_size, max_size), label="axes")
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
    smallest = minimal(nps.valid_tuple_axes(ndim, min_size, max_size))
    assert len(smallest) == min_size and all(k > -1 for k in smallest)


@settings(deadline=None, max_examples=10)
@given(ndim=st.integers(0, 3), data=st.data())
def test_minimize_negative_tuple_axes(ndim, data):
    min_size = data.draw(st.integers(0, ndim), label="min_size")
    max_size = data.draw(st.integers(min_size, ndim), label="max_size")
    smallest = minimal(
        nps.valid_tuple_axes(ndim, min_size, max_size), lambda x: all(i < 0 for i in x)
    )
    assert len(smallest) == min_size


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    shape=nps.array_shapes(min_side=0, max_side=4, min_dims=0, max_dims=3),
    data=st.data(),
)
def test_broadcastable_shape_bounds_are_satisfied(shape, data):
    min_dim = data.draw(st.integers(0, 4), label="min_dim")
    max_dim = data.draw(st.one_of(st.none(), st.integers(min_dim, 4)), label="max_dim")
    min_side = data.draw(st.integers(0, 3), label="min_side")
    max_side = data.draw(
        st.one_of(st.none(), st.integers(min_side, 6)), label="max_side"
    )
    try:
        bshape = data.draw(
            nps.broadcastable_shapes(
                shape,
                min_side=min_side,
                max_side=max_side,
                min_dims=min_dim,
                max_dims=max_dim,
            ),
            label="bshape",
        )
    except InvalidArgument:
        assume(False)

    if max_dim is None:
        max_dim = max(len(shape), min_dim) + 2

    if max_side is None:
        max_side = max(tuple(shape[::-1][:max_dim]) + (min_side,)) + 2

    assert isinstance(bshape, tuple) and all(isinstance(s, int) for s in bshape)
    assert min_dim <= len(bshape) <= max_dim
    assert all(min_side <= s <= max_side for s in bshape)


def _draw_valid_bounds(data, shape, max_dim, permit_none=True):
    if max_dim == 0 or not shape:
        return 0, None

    smallest_side = min(shape[::-1][:max_dim])
    min_strat = (
        st.sampled_from([1, smallest_side])
        if smallest_side > 1
        else st.just(smallest_side)
    )
    min_side = data.draw(min_strat, label="min_side")
    largest_side = max(max(shape[::-1][:max_dim]), min_side)
    if permit_none:
        max_strat = st.one_of(st.none(), st.integers(largest_side, largest_side + 2))
    else:
        max_strat = st.integers(largest_side, largest_side + 2)
    max_side = data.draw(max_strat, label="max_side")
    return min_side, max_side


@settings(deadline=None, max_examples=1000)
@given(
    shape=nps.array_shapes(min_dims=0, max_dims=6, min_side=1, max_side=5),
    data=st.data(),
)
def test_broadcastable_shape_has_good_default_values(shape, data):
    # This test ensures that default parameters can always produce broadcast-compatible shapes
    broadcastable_shape = data.draw(
        nps.broadcastable_shapes(shape), label="broadcastable_shapes"
    )
    a = np.zeros(shape, dtype="uint8")
    b = np.zeros(broadcastable_shape, dtype="uint8")
    np.broadcast(a, b)  # error if drawn shape for b is not broadcast-compatible


@settings(deadline=None)
@given(
    min_dim=st.integers(0, 5),
    shape=nps.array_shapes(min_dims=0, max_dims=3, min_side=0, max_side=10),
    data=st.data(),
)
def test_broadcastable_shape_can_broadcast(min_dim, shape, data):
    max_dim = data.draw(st.one_of(st.none(), st.integers(min_dim, 5)), label="max_dim")
    min_side, max_side = _draw_valid_bounds(data, shape, max_dim)
    broadcastable_shape = data.draw(
        nps.broadcastable_shapes(
            shape,
            min_side=min_side,
            max_side=max_side,
            min_dims=min_dim,
            max_dims=max_dim,
        ),
        label="broadcastable_shapes",
    )
    a = np.zeros(shape, dtype="uint8")
    b = np.zeros(broadcastable_shape, dtype="uint8")
    np.broadcast(a, b)  # error if drawn shape for b is not broadcast-compatible


@settings(deadline=None, max_examples=10)
@given(
    min_dim=st.integers(0, 5),
    shape=nps.array_shapes(min_dims=0, max_dims=3, min_side=0, max_side=5),
    data=st.data(),
)
def test_minimize_broadcastable_shape(min_dim, shape, data):
    # Ensure aligned dimensions of broadcastable shape minimizes to `(1,) * min_dim`
    max_dim = data.draw(st.one_of(st.none(), st.integers(min_dim, 5)), label="max_dim")
    min_side, max_side = _draw_valid_bounds(data, shape, max_dim, permit_none=False)
    smallest = minimal(
        nps.broadcastable_shapes(
            shape,
            min_side=min_side,
            max_side=max_side,
            min_dims=min_dim,
            max_dims=max_dim,
        )
    )
    note("(smallest): {}".format(smallest))
    n_leading = max(len(smallest) - len(shape), 0)
    n_aligned = max(len(smallest) - n_leading, 0)
    expected = [min_side] * n_leading + [
        1 if min_side <= 1 <= max_side else i for i in shape[len(shape) - n_aligned :]
    ]
    assert tuple(expected) == smallest


@settings(deadline=None)
@given(max_dim=st.integers(4, 6), data=st.data())
def test_broadcastable_shape_adjusts_max_dim_with_explicit_bounds(max_dim, data):
    # Ensures that `broadcastable_shapes` limits itself to satisfiable dimensions
    # Broadcastable values can only be drawn for dims 0-3 for these shapes
    shape = data.draw(st.sampled_from([(5, 3, 2, 1), (0, 3, 2, 1)]), label="shape")
    broadcastable_shape = data.draw(
        nps.broadcastable_shapes(
            shape, min_side=2, max_side=3, min_dims=3, max_dims=max_dim
        ),
        label="broadcastable_shapes",
    )
    assert len(broadcastable_shape) == 3
    a = np.zeros(shape, dtype="uint8")
    b = np.zeros(broadcastable_shape, dtype="uint8")
    np.broadcast(a, b)  # error if drawn shape for b is not broadcast-compatible


@settings(deadline=None, max_examples=10)
@given(min_dim=st.integers(0, 4), min_side=st.integers(2, 3), data=st.data())
def test_broadcastable_shape_shrinking_with_singleton_out_of_bounds(
    min_dim, min_side, data
):
    max_dim = data.draw(st.one_of(st.none(), st.integers(min_dim, 4)), label="max_dim")
    max_side = data.draw(
        st.one_of(st.none(), st.integers(min_side, 6)), label="max_side"
    )
    ndims = data.draw(st.integers(1, 4), label="ndim")
    shape = (1,) * ndims
    smallest = minimal(
        nps.broadcastable_shapes(
            shape,
            min_side=min_side,
            max_side=max_side,
            min_dims=min_dim,
            max_dims=max_dim,
        )
    )
    assert smallest == (min_side,) * min_dim


@settings(deadline=None)
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
    args = (
        dict(min_dims=min_dims) if min_dims is not None else {}
    )  # check default arg behavior too
    find_any(
        nps.broadcastable_shapes(shape, min_side=0, max_dims=max_dims, **args),
        lambda x: len(x) == desired_ndim,
        settings(max_examples=10 ** 6),
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


@settings(deadline=None, max_examples=10)
@given(
    shape=nps.array_shapes(min_dims=1, max_dims=2, min_side=1, max_side=3),
    data=st.data(),
)
def test_advanced_integer_index_can_generate_any_pattern(shape, data):
    # ensures that generated index-arrays can be used to yield any pattern of elements from an array
    x = np.arange(np.product(shape)).reshape(shape)

    target = data.draw(
        nps.arrays(
            shape=nps.array_shapes(min_dims=1, max_dims=2, min_side=1, max_side=2),
            elements=st.sampled_from(x.flatten()),
            dtype=x.dtype,
        ),
        label="target",
    )
    find_any(
        nps.integer_array_indices(
            shape, result_shape=st.just(target.shape), dtype=np.dtype("int8")
        ),
        lambda index: np.all(target == x[index]),
        settings(max_examples=10 ** 6),
    )


@pytest.mark.parametrize(
    "condition",
    [
        lambda ix: Ellipsis in ix,
        lambda ix: Ellipsis not in ix,
        lambda ix: np.newaxis in ix,
        lambda ix: np.newaxis not in ix,
    ],
)
def test_basic_indices_options(condition):
    indexers = nps.array_shapes(min_dims=0, max_dims=32).flatmap(
        lambda shape: nps.basic_indices(shape, allow_newaxis=True)
    )
    find_any(indexers, condition)


def test_basic_indices_can_generate_empty_tuple():
    find_any(nps.basic_indices(shape=(0, 0), allow_ellipsis=True), lambda ix: ix == ())


def test_basic_indices_can_generate_long_ellipsis():
    # Runs of slice(None) - such as [0,:,:,:,0] - can be replaced by e.g. [0,...,0]
    find_any(
        nps.basic_indices(shape=(1, 0, 0, 0, 1), allow_ellipsis=True),
        lambda ix: len(ix) == 3 and ix[1] == Ellipsis,
    )


@given(nps.basic_indices(shape=(0, 0, 0, 0, 0)).filter(lambda idx: Ellipsis in idx))
def test_basic_indices_replaces_whole_axis_slices_with_ellipsis(idx):
    # If ... is in the slice, it replaces all ,:, entries for this shape.
    assert slice(None) not in idx


@given(
    shape=nps.array_shapes(min_dims=0, max_side=4)
    | nps.array_shapes(min_dims=0, min_side=0, max_side=10),
    min_dims=st.integers(0, 5),
    allow_ellipsis=st.booleans(),
    allow_newaxis=st.booleans(),
    data=st.data(),
)
def test_basic_indices_generate_valid_indexers(
    shape, min_dims, allow_ellipsis, allow_newaxis, data
):
    max_dims = data.draw(st.none() | st.integers(min_dims, 32), label="max_dims")
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
        assert 0 <= len(indexer) <= len(shape) + int(allow_ellipsis)
        assert np.newaxis not in shape
    if not allow_ellipsis:
        assert Ellipsis not in shape

    if 0 in shape:
        # If there's a zero in the shape, the array will have no elements.
        array = np.zeros(shape)
        assert array.size == 0
    elif np.prod(shape) <= 10 ** 5:
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
