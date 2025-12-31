# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import typing
import warnings

import numpy as np
import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import SmallSearchSpaceWarning
from hypothesis.extra.numpy import ArrayLike, NDArray, _NestedSequence, _SupportsArray

from .test_from_dtype import STANDARD_TYPES
from tests.common.debug import assert_simple_property, find_any

STANDARD_TYPES_TYPE = [dtype.type for dtype in STANDARD_TYPES]

needs_np_typing = {"reason": "numpy.typing is not available"}
needs_np_private_typing = {"reason": "numpy._typing is not available"}


@given(dtype=st.from_type(np.dtype))
def test_resolves_dtype_type(dtype):
    assert isinstance(dtype, np.dtype)


def test_does_not_resolve_nonscalar_types():
    # this was previously a parametrized test over np.object_ and np.void which
    # used the same repr code path for the test. But then numpy changed their types
    # such that we defer evaluation for st.from_type and are no longer identical
    # to st.builds, but rather something morally equivalent to it. So we have
    # these slightly more complicated checks.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SmallSearchSpaceWarning)
        assert_simple_property(st.from_type(np.object_), lambda value: value is None)

    with pytest.raises(TypeError):
        # np.void() requires an argument, and so throws when instantiated
        assert_simple_property(st.from_type(np.void))


@pytest.mark.parametrize("typ", STANDARD_TYPES_TYPE)
def test_resolves_and_varies_numpy_scalar_type(typ):
    # Check that we find an instance that is not equal to the default
    x = find_any(st.from_type(typ), lambda x: x != type(x)())
    assert isinstance(x, typ)


@pytest.mark.parametrize("atype", [np.ndarray, NDArray])
def test_resolves_unspecified_array_type(atype):
    if atype is not None:
        assert_simple_property(st.from_type(atype), lambda v: isinstance(v, np.ndarray))


def workaround(dtype):
    # Total hack to work around https://github.com/numpy/numpy/issues/24043
    if np.__version__ == "1.25.0" and dtype == np.dtype("bytes").type:
        return pytest.param(dtype, marks=[pytest.mark.xfail(strict=False)])
    return dtype


# https://numpy.org/devdocs/release/1.22.0-notes.html#ndarray-dtype-and-number-are-now-runtime-subscriptable
@pytest.mark.skipif(
    tuple(int(x) for x in np.__version__.split(".")[:2]) < (1, 22), reason="see comment"
)
@pytest.mark.parametrize("typ", [workaround(t) for t in STANDARD_TYPES_TYPE])
def test_resolves_specified_ndarray_type(typ):
    assert_simple_property(
        st.from_type(np.ndarray[typ]),
        lambda arr: isinstance(arr, np.ndarray) and arr.dtype.type == typ,
    )

    assert_simple_property(
        st.from_type(np.ndarray[typing.Any, typ]),
        lambda arr: isinstance(arr, np.ndarray) and arr.dtype.type == typ,
    )


@pytest.mark.skipif(NDArray is None, **needs_np_typing)
@pytest.mark.parametrize("typ", [workaround(t) for t in STANDARD_TYPES_TYPE])
def test_resolves_specified_NDArray_type(typ):
    assert_simple_property(
        st.from_type(NDArray[typ]),
        lambda arr: isinstance(arr, np.ndarray) and arr.dtype.type == typ,
    )


@pytest.mark.skipif(NDArray is None, **needs_np_typing)
def test_resolves_NDArray_with_dtype_union():
    strat = st.from_type(NDArray[np.float64 | np.complex128])
    find_any(strat, lambda arr: arr.dtype == np.dtype("float64"))
    find_any(strat, lambda arr: arr.dtype == np.dtype("complex128"))


@pytest.mark.skipif(ArrayLike is None, **needs_np_typing)
@given(arr_like=st.from_type(ArrayLike))
def test_resolves_ArrayLike_type(arr_like):
    arr = np.array(arr_like)
    assert isinstance(arr, np.ndarray)
    # The variation is too large to assert anything else about arr, but the
    # ArrayLike contract just says that it can be coerced into an array (which
    # we just did).


@pytest.mark.skipif(_NestedSequence is None, **needs_np_private_typing)
def test_resolves_specified_NestedSequence():
    @given(seq=st.from_type(_NestedSequence[int]))
    def test(seq):
        assert hasattr(seq, "__iter__")

        def flatten(lst):
            for el in lst:
                try:
                    yield from flatten(el)
                except TypeError:
                    yield el

        assert all(isinstance(i, int) for i in flatten(seq))

    test()


@pytest.mark.skipif(_NestedSequence is None, **needs_np_private_typing)
@given(seq=st.from_type(_NestedSequence))
def test_resolves_unspecified_NestedSequence(seq):
    assert hasattr(seq, "__iter__")


@pytest.mark.skipif(_SupportsArray is None, **needs_np_private_typing)
@given(arr=st.from_type(_SupportsArray))
def test_resolves_unspecified_SupportsArray(arr):
    assert hasattr(arr, "__array__")


@pytest.mark.skipif(_SupportsArray is None, **needs_np_private_typing)
def test_resolves_SupportsArray():
    @given(arr=st.from_type(_SupportsArray[int]))
    def test(arr):
        assert hasattr(arr, "__array__")
        assert np.asarray(arr).dtype.kind == "i"

    test()


@pytest.mark.skipif(
    _NestedSequence is None or _SupportsArray is None, **needs_np_private_typing
)
def test_resolve_ArrayLike_equivalent():
    # This is the current (1.24.3) definition of ArrayLike,
    # with problematic parts commented out.
    ArrayLike_like = (
        _SupportsArray
        # | _NestedSequence[_SupportsArray],
        | bool
        | int
        | float
        | complex
        | str
        | bytes
        | _NestedSequence[
            bool | int | float | complex | str,
            # | bytes,
        ]
    )

    @given(arr_like=st.from_type(ArrayLike_like))
    def test(arr_like):
        arr = np.array(arr_like)
        assert isinstance(arr, np.ndarray)

    test()
