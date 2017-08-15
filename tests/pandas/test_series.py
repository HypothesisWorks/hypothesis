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
from tests.common.debug import find_any
from hypothesis.internal.compat import text_type


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


LABELS = ['A', 'B', 'C', 'D', 'E']


@given(pdst.series(st.sampled_from(LABELS), dtype='category'))
def test_categorical_series(s):
    assert set(s).issubset(set(LABELS))
    assert s.dtype == 'category'


@given(pdst.series(dtype=st.sampled_from((np.int64, str)), min_size=1))
def test_can_specify_dtype_as_strategy(s):
    assert isinstance(s[0], (np.int64, str))


@given(pdst.series(index=st.lists(st.text(min_size=1), unique=True)))
def test_index_can_be_a_strategy(df):
    assert all(isinstance(i, text_type) for i in df.index)


@given(pdst.series(
    index=st.lists(st.text(min_size=1), unique=True), max_size=1))
def test_index_strategy_respects_max_size(df):
    assert all(isinstance(i, text_type) for i in df.index)
    assert len(df) <= 1


def test_will_error_on_bad_index():
    with pytest.raises(InvalidArgument):
        pdst.series(index=1).example()


@given(pdst.series(min_size=3, index=[0, 1, 2]))
def test_will_pick_up_max_size_from_index(s):
    assert len(s) == 3


def test_too_short_index_is_an_error():
    with pytest.raises(InvalidArgument):
        pdst.series(index=[1], max_size=2).example()
