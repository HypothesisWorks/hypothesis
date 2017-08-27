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
import pytest

import hypothesis.strategies as st
import hypothesis.extra.numpy as npst
import hypothesis.extra.pandas as pdst
from hypothesis import given, assume, reject
from hypothesis.errors import InvalidArgument
from tests.pandas.helpers import supported_by_pandas


@given(st.data())
def test_can_create_a_series_of_any_dtype(data):
    dtype = np.dtype(data.draw(npst.scalar_dtypes()))
    assume(supported_by_pandas(dtype))
    series = data.draw(pdst.series(dtype=dtype))
    assert series.dtype == dtype


@given(st.data())
def test_buggy_dtype_identification_is_precise(data):
    dtype = np.dtype(data.draw(npst.scalar_dtypes()))
    assume(not supported_by_pandas(dtype))
    try:
        series = data.draw(pdst.series(dtype=dtype))
    except Exception as e:
        if type(e).__name__ != 'OutOfBoundsDatetime':
            raise
        reject()
    assert series.dtype != dtype


@given(pdst.series(
    dtype=float, index=pdst.range_indexes(min_size=2, max_size=5)))
def test_series_respects_size_bounds(s):
    assert 2 <= len(s) <= 5


@given(pdst.series(dtype=int))
def test_can_generate_integral_series(s):
    assert s.dtype == np.dtype(int)


@given(pdst.series(elements=st.integers(0, 10)))
def test_will_use_dtype_of_elements(s):
    assert s.dtype == np.dtype(int)


@given(pdst.series(elements=st.floats(allow_nan=False)))
def test_will_use_a_provided_elements_strategy(s):
    assert all(x == x for x in s)


LABELS = ['A', 'B', 'C', 'D', 'E']


@given(pdst.series(st.sampled_from(LABELS), dtype='category'))
def test_categorical_series(s):
    assert set(s).issubset(set(LABELS))
    assert s.dtype == 'category'


def test_will_error_on_bad_index():
    with pytest.raises(InvalidArgument):
        pdst.series(index=1).example()
