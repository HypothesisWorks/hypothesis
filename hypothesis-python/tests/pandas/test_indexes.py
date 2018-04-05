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

from __future__ import division, print_function, absolute_import

import numpy as np
import pytest

import pandas
import hypothesis.strategies as st
import hypothesis.extra.numpy as npst
import hypothesis.extra.pandas as pdst
from hypothesis import HealthCheck, given, assume, reject, settings
from hypothesis.errors import NoExamples
from tests.pandas.helpers import supported_by_pandas


@given(pdst.indexes(dtype=int, max_size=0))
def test_gets_right_dtype_for_empty_indices(ix):
    assert ix.dtype == np.dtype('int64')


def test_does_not_generate_impossible_conditions():
    with pytest.raises(NoExamples):
        pdst.indexes(
            min_size=3, max_size=3, dtype=bool
        ).example()


@given(pdst.indexes(dtype=bool, unique=True))
def test_unique_indexes_of_small_values(ix):
    assert len(ix) <= 2
    assert len(set(ix)) == len(ix)


# Sizes that fit into an int64 without overflow
range_sizes = st.integers(0, 2 ** 63 - 1)


@given(range_sizes, range_sizes | st.none(), st.data())
def test_arbitrary_range_index(i, j, data):
    if j is not None:
        i, j = sorted((i, j))
    data.draw(pdst.range_indexes(i, j))


@given(pdst.range_indexes())
def test_basic_range_indexes(ix):
    assert isinstance(ix, pandas.RangeIndex)


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(st.data())
def test_generate_arbitrary_indices(data):
    min_size = data.draw(st.integers(0, 10), 'min_size')
    max_size = data.draw(
        st.none() | st.integers(min_size, min_size + 10), 'max_size')
    unique = data.draw(st.booleans(), 'unique')
    dtype = data.draw(npst.scalar_dtypes(), 'dtype')
    assume(supported_by_pandas(dtype))

    # Pandas bug: https://github.com/pandas-dev/pandas/pull/14916 until 0.20;
    # then int64 indexes are inferred from uint64 values.
    assume(dtype.kind != 'u')

    pass_elements = data.draw(st.booleans(), 'pass_elements')

    converted_dtype = pandas.Index([], dtype=dtype).dtype

    try:
        inferred_dtype = pandas.Index(
            [data.draw(npst.from_dtype(dtype))]).dtype

        if pass_elements:
            elements = npst.from_dtype(dtype)
            dtype = None
        else:
            elements = None

        index = data.draw(pdst.indexes(
            elements=elements, dtype=dtype, min_size=min_size,
            max_size=max_size, unique=unique,
        ))

    except Exception as e:
        if type(e).__name__ == 'OutOfBoundsDatetime':
            # See https://github.com/HypothesisWorks/hypothesis-python/pull/826
            reject()
        else:
            raise
    if dtype is None:
        if pandas.__version__ >= '0.19':
            assert index.dtype == inferred_dtype
    else:
        assert index.dtype == converted_dtype

    if unique:
        assert len(set(index.values)) == len(index)
