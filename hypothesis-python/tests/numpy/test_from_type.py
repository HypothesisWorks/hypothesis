import numpy as np
import numpy.typing as npt
import pytest

from hypothesis import given
from hypothesis.strategies import from_type

from tests.common.debug import find_any

from .test_from_dtype import STANDARD_TYPES

@given(dtype=from_type(np.dtype))
def test_resolves_dtype_type(dtype):
    assert isinstance(dtype, np.dtype)


@pytest.mark.parametrize("dtype", STANDARD_TYPES)
def test_resolves_and_varies_numpy_scalar_type(dtype):
    # Check that we find an instance that is not equal to the default
    x = find_any(from_type(dtype.type), lambda x: x != type(x)())
    assert isinstance(x, dtype.type)


@pytest.mark.parametrize("atype", [np.ndarray, npt.NDArray])
def test_resolves_unspecified_array_type(atype):
    s = from_type(atype)
    assert isinstance(s.example(), np.ndarray)


@pytest.mark.parametrize("atype", [np.ndarray, npt.NDArray])
@pytest.mark.parametrize("dtype", STANDARD_TYPES)
def test_resolves_specified_array_type(atype, dtype):
    typ = atype[dtype.type]
    s = from_type(typ)
    assert isinstance(s.example(), np.ndarray)
    assert s.example().dtype.kind == dtype.kind
