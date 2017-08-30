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
import hypothesis.extra.pandas as pdst
from hypothesis import given
from hypothesis.errors import InvalidArgument


@given(pdst.data_frames([
    pdst.column('a', dtype=int),
    pdst.column('b', dtype=float),
]))
def test_can_have_columns_of_distinct_types(df):
    assert df['a'].dtype == np.dtype(int)
    assert df['b'].dtype == np.dtype(float)


@given(pdst.data_frames(
    [pdst.column(dtype=int)],
    index=pdst.range_indexes(min_size=1, max_size=5)))
def test_respects_size_bounds(df):
    assert 1 <= len(df) <= 5


@given(pdst.data_frames(pdst.columns(['A', 'B'], dtype=float)))
def test_can_specify_just_column_names(df):
    df['A']
    df['B']


@given(pdst.data_frames(
    rows=st.fixed_dictionaries({'A': st.integers(1, 10), 'B': st.floats()}))
)
def test_gets_the_correct_data_shape_for_just_rows(table):
    assert table['A'].dtype == np.dtype(int)
    assert table['B'].dtype == np.dtype(float)


def test_validates_against_duplicate_columns():
    with pytest.raises(InvalidArgument):
        pdst.data_frames(['A', 'A']).example()


def test_requires_elements_for_category():
    with pytest.raises(InvalidArgument):
        pdst.data_frames([pdst.column('A', dtype='category')]).example()
