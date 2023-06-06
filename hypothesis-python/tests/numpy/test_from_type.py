import sys
import typing

import numpy as np
import numpy.typing as npt
import pytest

from hypothesis import assume, given
from hypothesis.strategies import from_type

from tests.common.debug import find_any

from .test_from_dtype import STANDARD_TYPES
STANDARD_TYPES_TYPE = [dtype.type for dtype in STANDARD_TYPES]

@given(dtype=from_type(np.dtype))
def test_resolves_dtype_type(dtype):
    assert isinstance(dtype, np.dtype)


@pytest.mark.parametrize("typ", STANDARD_TYPES_TYPE)
def test_resolves_and_varies_numpy_scalar_type(typ):
    # Check that we find an instance that is not equal to the default
    x = find_any(from_type(typ), lambda x: x != type(x)())
    assert isinstance(x, typ)


@pytest.mark.parametrize("atype", [np.ndarray, npt.NDArray])
def test_resolves_unspecified_array_type(atype):
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


@pytest.mark.parametrize("typ", STANDARD_TYPES_TYPE)
def test_resolves_specified_NDArray_type(typ):
    arr = from_type(npt.NDArray[typ]).example()
    assert isinstance(arr, np.ndarray)
    assert arr.dtype.type == typ


@given(arr_like=from_type(npt.ArrayLike))
def test_resolves_ArrayLike_type(arr_like):
    arr = np.array(arr_like)
    assert isinstance(arr, np.ndarray)
    # The variation is too large to assert anything else about arr, but the
    # ArrayLike contract just says that it can be coerced intto an array (which
    # we just did).
