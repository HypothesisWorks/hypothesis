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
from hypothesis import given, example
from hypothesis.types import RandomWithSeed as Random
from tests.common.debug import minimal


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


@given(pdst.data_frames(pdst.columns(2, dtype=float)))
def test_can_specify_just_column_count(df):
    df[0]
    df[1]


@given(pdst.data_frames(
    rows=st.fixed_dictionaries({'A': st.integers(1, 10), 'B': st.floats()}))
)
def test_gets_the_correct_data_shape_for_just_rows(table):
    assert table['A'].dtype == np.dtype(int)
    assert table['B'].dtype == np.dtype(float)


@given(pdst.data_frames(
    columns=pdst.columns(['A', 'B'], dtype=int),
    rows=st.lists(st.integers(0, 1000), min_size=2, max_size=2).map(sorted),
))
def test_can_specify_both_rows_and_columns_list(d):
    assert d['A'].dtype == np.dtype(int)
    assert d['B'].dtype == np.dtype(int)
    for _, r in d.iterrows():
        assert r['A'] <= r['B']


@given(pdst.data_frames(
    columns=pdst.columns(['A', 'B'], dtype=int),
    rows=st.lists(
        st.integers(0, 1000), min_size=2, max_size=2).map(sorted).map(tuple),
))
def test_can_specify_both_rows_and_columns_tuple(d):
    assert d['A'].dtype == np.dtype(int)
    assert d['B'].dtype == np.dtype(int)
    for _, r in d.iterrows():
        assert r['A'] <= r['B']


@given(pdst.data_frames(
    columns=pdst.columns(['A', 'B'], dtype=int),
    rows=st.lists(st.integers(0, 1000), min_size=2, max_size=2).map(
        lambda x: {'A': min(x), 'B': max(x)}),
))
def test_can_specify_both_rows_and_columns_dict(d):
    assert d['A'].dtype == np.dtype(int)
    assert d['B'].dtype == np.dtype(int)
    for _, r in d.iterrows():
        assert r['A'] <= r['B']


@given(
    pdst.data_frames([pdst.column('A', fill=st.just(float('nan')),
                                  elements=st.floats(allow_nan=False))],
                     rows=st.builds(dict)))
def test_can_fill_in_missing_elements_from_dict(df):
    assert np.isnan(df['A']).all()


subsets = ['', 'A', 'B', 'C', 'AB', 'AC', 'BC', 'ABC']


@pytest.mark.parametrize('disable_fill', subsets)
@pytest.mark.parametrize('non_standard_index', [True, False])
@example(True, False)
def test_can_minimize_based_on_two_columns_independently(
    disable_fill, non_standard_index
):
    columns = [
        pdst.column(
            name, dtype=bool,
            fill=st.nothing() if name in disable_fill else None,
        )
        for name in ['A', 'B', 'C']
    ]

    x = minimal(
        pdst.data_frames(
            columns,
            index=pdst.indexes(dtype=int) if non_standard_index else None,
        ),
        lambda x: x['A'].any() and x['B'].any() and x['C'].any(),
        random=Random(0),
    )
    assert len(x['A']) == 1
    assert x['A'][0] == 1
    assert x['B'][0] == 1
    assert x['C'][0] == 1
