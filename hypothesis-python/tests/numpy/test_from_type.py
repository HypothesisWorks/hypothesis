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
import typing

import numpy as np
import pytest

from hypothesis import given
from hypothesis.extra.numpy import ArrayLike, NDArray, _NestedSequence, _SupportsArray
from hypothesis.strategies import builds, from_type

from .test_from_dtype import STANDARD_TYPES
from tests.common.debug import find_any

STANDARD_TYPES_TYPE = [dtype.type for dtype in STANDARD_TYPES]


@given(dtype=from_type(np.dtype))
def test_resolves_dtype_type(dtype):
    assert isinstance(dtype, np.dtype)


@pytest.mark.parametrize("typ", [np.object_, np.void])
def test_does_not_resolve_nonscalar_types(typ):
    # Comparing the objects directly fails on Windows,
    # so compare their reprs instead.
    assert repr(from_type(typ)) == repr(builds(typ))


@pytest.mark.parametrize("typ", STANDARD_TYPES_TYPE)
def test_resolves_and_varies_numpy_scalar_type(typ):
    # Check that we find an instance that is not equal to the default
    x = find_any(from_type(typ), lambda x: x != type(x)())
    assert isinstance(x, typ)


@pytest.mark.parametrize("atype", [np.ndarray, NDArray])
def test_resolves_unspecified_array_type(atype):
    if atype is not None:
        assert isinstance(from_type(atype).example(), np.ndarray)


@pytest.mark.skipif(
    sys.version_info[:2] < (3, 9),
    reason="Type subscription requires python >= 3.9",
)
@pytest.mark.parametrize("typ", STANDARD_TYPES_TYPE)
def test_resolves_specified_ndarray_type(typ):
    arr = from_type(np.ndarray[typ]).example()
    assert isinstance(arr, np.ndarray)
    assert arr.dtype.type == typ

    arr = from_type(np.ndarray[typing.Any, typ]).example()
    assert isinstance(arr, np.ndarray)
    assert arr.dtype.type == typ


@pytest.mark.skipif(
    NDArray is None,
    reason="numpy.typing is not available",
)
@pytest.mark.parametrize("typ", STANDARD_TYPES_TYPE)
def test_resolves_specified_NDArray_type(typ):
    arr = from_type(NDArray[typ]).example()
    assert isinstance(arr, np.ndarray)
    assert arr.dtype.type == typ


@pytest.mark.skipif(
    ArrayLike is None,
    reason="numpy.typing is not available",
)
@given(arr_like=from_type(ArrayLike))
def test_resolves_ArrayLike_type(arr_like):
    arr = np.array(arr_like)
    assert isinstance(arr, np.ndarray)
    # The variation is too large to assert anything else about arr, but the
    # ArrayLike contract just says that it can be coerced into an array (which
    # we just did).


@pytest.mark.skipif(
    _NestedSequence is None,
    reason="numpy._typing is not available",
)
def test_resolves_specified_NestedSequence():
    @given(seq=from_type(_NestedSequence[int]))
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


@pytest.mark.skipif(
    _NestedSequence is None,
    reason="numpy._typing is not available",
)
@given(seq=from_type(_NestedSequence))
def test_resolves_unspecified_NestedSequence(seq):
    assert hasattr(seq, "__iter__")


@pytest.mark.skipif(
    _SupportsArray is None,
    reason="numpy._typing is not available",
)
@given(arr=from_type(_SupportsArray))
def test_resolves_unspecified_SupportsArray(arr):
    assert hasattr(arr, "__array__")


@pytest.mark.skipif(
    _SupportsArray is None,
    reason="numpy._typing is not available",
)
def test_resolves_SupportsArray():
    @given(arr=from_type(_SupportsArray[int]))
    def test(arr):
        assert hasattr(arr, "__array__")
        assert np.asarray(arr).dtype.kind == "i"

    test()


@pytest.mark.skipif(
    _NestedSequence is None or _SupportsArray is None,
    reason="numpy._typing is not available",
)
def test_resolve_ArrayLike_equivalent():
    # This is the current (1.24.3) definition of ArrayLike,
    # with problematic parts commented out.
    ArrayLike_like = typing.Union[
        _SupportsArray,
        # _NestedSequence[_SupportsArray],
        bool,
        int,
        float,
        complex,
        str,
        bytes,
        _NestedSequence[
            typing.Union[
                bool,
                int,
                float,
                complex,
                str,
                # bytes,
            ]
        ],
    ]

    @given(arr_like=from_type(ArrayLike_like))
    def test(arr_like):
        arr = np.array(arr_like)
        assert isinstance(arr, np.ndarray)

    test()
