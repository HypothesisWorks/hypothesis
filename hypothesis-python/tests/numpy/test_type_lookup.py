# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import numpy as np
import pytest
from numpy.typing import NDArray

from hypothesis import given, strategies as st

from tests.common.debug import assert_all_examples


def test_from_numpy_ndarray_any_type():
    assert_all_examples(st.from_type(NDArray), lambda obj: isinstance(obj, np.ndarray))


@pytest.mark.parametrize(
    "test_nptype",
    [
        np.float64,
        np.int32,
        np.uint64,
        np.int16,
        np.uint8,
        np.complex128,
    ],
)
def test_from_numpy_ndarray_specific_type(test_nptype):
    assert_all_examples(
        st.from_type(NDArray[test_nptype]), lambda obj: obj.dtype == test_nptype
    )


@given(...)
def test_numpy_str(x: np.ndarray):
    assert isinstance(x, np.ndarray)
