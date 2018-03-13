# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import sys

import numpy as np
import pytest
from flaky import flaky

import hypothesis.strategies as st
import hypothesis.extra.numpy as nps
from hypothesis import given, assume, settings
from hypothesis.errors import InvalidArgument
from tests.common.debug import minimal, find_any
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import text_type, binary_type

STANDARD_TYPES = list(map(np.dtype, [
    u'int8', u'int32', u'int64',
    u'float', u'float32', u'float64',
    complex,
    u'datetime64', u'timedelta64',
    bool, text_type, binary_type
]))


@given(nps.nested_dtypes())
def test_strategies_for_standard_dtypes_have_reusable_values(dtype):
    assert nps.from_dtype(dtype).has_reusable_values


@pytest.mark.parametrize(u't', STANDARD_TYPES)
def test_produces_instances(t):
    @given(nps.from_dtype(t))
    def test_is_t(x):
        assert isinstance(x, t.type)
        assert x.dtype.kind == t.kind
    test_is_t()


@given(nps.arrays(float, ()))
def test_empty_dimensions_are_scalars(x):
    assert isinstance(x, np.dtype(float).type)


@given(nps.arrays(float, (1, 0, 1)))
def test_can_handle_zero_dimensions(x):
    assert x.shape == (1, 0, 1)


@given(nps.arrays(u'uint32', (5, 5)))
def test_generates_unsigned_ints(x):
    assert (x >= 0).all()


@given(nps.arrays(int, (1,)))
def test_assert_fits_in_machine_size(x):
    pass


def test_generates_and_minimizes():
    assert (minimal(nps.arrays(float, (2, 2))) == np.zeros(shape=(2, 2))).all()


def test_can_minimize_large_arrays():
    x = minimal(
        nps.arrays(u'uint32', 100), lambda x: np.any(x) and not np.all(x),
        timeout_after=60
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


def test_can_create_arrays_of_tuples():
    arr = minimal(
        nps.arrays(object, 10, st.tuples(st.integers(), st.integers())),
        lambda x: all(t0 != t1 for t0, t1 in x))
    assert all(a in ((1, 0), (0, 1)) for a in arr)


@given(nps.arrays(object, (2, 2), st.tuples(st.integers())))
def test_does_not_flatten_arrays_of_tuples(arr):
    assert isinstance(arr[0][0], tuple)


@given(
    nps.arrays(object, (2, 2), st.lists(st.integers(), min_size=1, max_size=1))
)
def test_does_not_flatten_arrays_of_lists(arr):
    assert isinstance(arr[0][0], list)


@given(nps.array_shapes())
def test_can_generate_array_shapes(shape):
    assert isinstance(shape, tuple)
    assert all(isinstance(i, int) for i in shape)


@settings(deadline=None)
@given(st.integers(1, 10), st.integers(0, 9), st.integers(1), st.integers(0))
def test_minimise_array_shapes(min_dims, dim_range, min_side, side_range):
    smallest = minimal(nps.array_shapes(min_dims, min_dims + dim_range,
                                        min_side, min_side + side_range))
    assert len(smallest) == min_dims and all(k == min_side for k in smallest)


@given(nps.scalar_dtypes())
def test_can_generate_scalar_dtypes(dtype):
    assert isinstance(dtype, np.dtype)


@given(nps.nested_dtypes())
def test_can_generate_compound_dtypes(dtype):
    assert isinstance(dtype, np.dtype)


@given(nps.nested_dtypes(max_itemsize=settings.default.buffer_size // 10),
       st.data())
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
    assert minimal(nps.scalar_dtypes()) == np.dtype(u'bool')


def test_minimise_nested_types():
    assert minimal(nps.nested_dtypes()) == np.dtype(u'bool')


def test_minimise_array_strategy():
    smallest = minimal(nps.arrays(
        nps.nested_dtypes(max_itemsize=settings.default.buffer_size // 3**3),
        nps.array_shapes(max_dims=3, max_side=3)))
    assert smallest.dtype == np.dtype(u'bool') and not smallest.any()


@given(nps.array_dtypes(allow_subarrays=False))
def test_can_turn_off_subarrays(dt):
    for field, _ in dt.fields.values():
        assert field.shape == ()


@pytest.mark.parametrize('byteorder', ['<', '>'])
@given(data=st.data())
def test_can_restrict_endianness(data, byteorder):
    dtype = data.draw(nps.integer_dtypes(byteorder, sizes=(16, 32, 64)))
    if byteorder == ('<' if sys.byteorder == 'little' else '>'):
        assert dtype.byteorder == '='
    else:
        assert dtype.byteorder == byteorder


@given(nps.integer_dtypes(sizes=8))
def test_can_specify_size_as_an_int(dt):
    assert dt.itemsize == 1


@given(st.data())
def test_can_draw_shapeless_from_scalars(data):
    dt = data.draw(nps.scalar_dtypes())
    result = data.draw(nps.arrays(dtype=dt, shape=()))
    assert isinstance(result, dt.type)


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


@given(nps.arrays(dtype='int8', shape=st.integers(0, 20), unique=True))
def test_array_values_are_unique(arr):
    assert len(set(arr)) == len(arr)


def test_may_fill_with_nan_when_unique_is_set():
    find_any(
        nps.arrays(
            dtype=float, elements=st.floats(allow_nan=False), shape=10,
            unique=True, fill=st.just(float('nan'))),
        lambda x: np.isnan(x).any()
    )


def test_is_still_unique_with_nan_fill():
    @given(nps.arrays(
           dtype=float, elements=st.floats(allow_nan=False), shape=10,
           unique=True, fill=st.just(float('nan'))))
    def test(xs):
        assert len(set(xs)) == len(xs)

    test()


def test_may_not_fill_with_non_nan_when_unique_is_set():
    @given(nps.arrays(
        dtype=float, elements=st.floats(allow_nan=False), shape=10,
        unique=True, fill=st.just(0.0)))
    def test(arr):
        pass

    with pytest.raises(InvalidArgument):
        test()


def test_may_not_fill_with_non_nan_when_unique_is_set_and_type_is_not_number():
    @given(nps.arrays(
        dtype=bytes, shape=10,
        unique=True, fill=st.just(b'')))
    def test(arr):
        pass

    with pytest.raises(InvalidArgument):
        test()


@given(st.data(),
       st.builds('{}[{}]'.format,
                 st.sampled_from(('datetime64', 'timedelta64')),
                 st.sampled_from(nps.TIME_RESOLUTIONS)
                 ).map(np.dtype)
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
