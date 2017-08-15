# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

import numpy as np

import hypothesis.strategies as st
import hypothesis.extra.numpy as npst
import hypothesis.extra.pandas as pdst
from hypothesis import given, assume, reject
from tests.common.debug import find_any


@given(st.data())
def test_can_create_a_series_of_any_dtype(data):
    dtype = np.dtype(data.draw(npst.scalar_dtypes()))
    assume(pdst.supported_by_pandas(dtype))
    series = data.draw(pdst.series(dtype=dtype))
    assert series.dtype == dtype


@given(st.data())
def test_buggy_dtype_identification_is_precise(data):
    dtype = np.dtype(data.draw(npst.scalar_dtypes()))
    assume(not pdst.supported_by_pandas(dtype))
    try:
        series = data.draw(pdst.series(dtype=dtype))
    except Exception as e:
        if type(e).__name__ != 'OutOfBoundsDatetime':
            raise
        reject()
    assert series.dtype != dtype


@given(pdst.series(min_size=2, max_size=5))
def test_series_respects_size_bounds(s):
    assert 2 <= len(s) <= 5


@given(pdst.series(dtype=int))
def test_can_generate_integral_series(s):
    assert s.dtype == np.dtype(int)


@given(pdst.series(elements=st.integers(0, 1000)))
def test_will_use_default_dtype_regardless_of_elements(s):
    assert s.dtype == np.dtype(float)


@given(pdst.series(elements=st.floats(allow_nan=False)))
def test_will_use_a_provided_elements_strategy(s):
    assert all(x == x for x in s)


REVERSE_INDEX = list(range(5, 0, -1))


@given(pdst.series(index=REVERSE_INDEX))
def test_can_use_index_to_bound_size(s):
    assert len(s) <= len(REVERSE_INDEX)
    assert list(s.index) == REVERSE_INDEX[:len(s)]


def test_does_not_have_to_use_the_full_index():
    find_any(
        pdst.series(index=REVERSE_INDEX), lambda x: len(x) < len(REVERSE_INDEX)
    )
