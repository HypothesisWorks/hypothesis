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

from __future__ import absolute_import, division, print_function

import numpy as np

from hypothesis import given
from hypothesis.extra.numpy import from_dtype, integer_dtypes
from hypothesis.strategies import data, floats, integers


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
