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

from hypothesis import given
from hypothesis.extra.numpy import arrays, from_dtype, integer_dtypes
from hypothesis.strategies import data, floats, integers


@pytest.mark.parametrize("dtype", [np.float16, np.float32, np.float64])
@pytest.mark.parametrize("low", [-2.0, -1.0, 0.0, 1.0])
@given(data())
def test_bad_float_exclude_min_in_array(dtype, low, data):
    elements = floats(
        low, low + 1, exclude_min=True, width=np.dtype(dtype).itemsize * 8
    )
    x = data.draw(arrays(dtype, shape=(1,), elements=elements), label="x")
    assert np.all(low < x)


@given(floats(width=32))
def test_float32_exactly_representable(x):
    clipped = np.dtype("float32").type(x)
    if np.isnan(x):
        assert np.isnan(clipped)
    else:
        assert x == float(clipped)


@given(floats(width=16))
def test_float16_exactly_representable(x):
    clipped = np.dtype("float16").type(x)
    if np.isnan(x):
        assert np.isnan(clipped)
    else:
        assert x == float(clipped)


@given(data=data(), dtype=integer_dtypes())
def test_floor_ceil_lossless(data, dtype):
    # Regression test for issue #1667; ceil converting numpy integers
    # to float and back to int with loss of exact value.
    x = data.draw(from_dtype(dtype))
    assert data.draw(integers(x, x)) == x
