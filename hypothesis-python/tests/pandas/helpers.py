# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
from dataclasses import field, dataclass

import numpy as np

from hypothesis.extra import numpy as npst
from hypothesis import strategies as st

PANDAS_TIME_DTYPES = tuple(map(np.dtype, ["<M8[ns]", "<m8[ns]", ">M8[ns]", ">m8[ns]"]))


def supported_by_pandas(dtype):
    """Checks whether the dtype is one that can be correctly handled by
    Pandas."""
    # Pandas does not support non-native byte orders and things go amusingly
    # wrong in weird places if you try to use them. See
    # https://pandas.pydata.org/pandas-docs/stable/gotchas.html#byte-ordering-issues
    if dtype.byteorder not in ("|", "="):
        return False

    # Pandas only supports a limited range of timedelta and datetime dtypes
    # compared to the full range that numpy supports and will convert
    # everything to those types (possibly increasing precision in the course of
    # doing so, which can cause problems if this results in something which
    # does not fit into the desired word type. As a result we want to filter
    # out any timedelta or datetime dtypes that are not of the desired types.
    if dtype.kind in ("m", "M"):
        return dtype in PANDAS_TIME_DTYPES
    return True


@dataclass(unsafe_hash=True)
class MyTestClass:
    a: int = 1
    b: str = "hello"
    c: np.ndarray = np.array([1, 2])
    d: dict[str, dict[str, float]] = field(default_factory=lambda: {"x": {"y": 1.0}})
dataclass_instance = MyTestClass()


all_scalar_object_elements = st.one_of(
    st.just(dataclass_instance),
    st.from_type(type).filter(lambda x: st.from_type(x).supports_find).flatmap(st.from_type).filter(npst._is_compatible_numpy_element_object),
)

all_numpy_dtype_elements = st.one_of(npst.scalar_dtypes(), npst.array_dtypes())

all_scalar_elements = st.one_of(all_numpy_dtype_elements, all_scalar_object_elements)

all_object_arrays = npst.arrays(np.dtype('O'), elements=all_scalar_elements, shape=npst.array_shapes(min_dims=1, min_side=1))

all_elements = st.one_of(
    all_scalar_elements,
    all_object_arrays
)
