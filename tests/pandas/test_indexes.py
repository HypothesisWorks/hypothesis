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

import pandas
import hypothesis.strategies as st
import hypothesis.extra.numpy as npst
import hypothesis.extra.pandas as pdst
from hypothesis import given, assume
from hypothesis.errors import NoExamples
from tests.pandas.helpers import supported_by_pandas
from hypothesis.extra.pandas.impl import is_ordered_dtype_for_index


def test_does_not_generate_impossible_conditions():
    with pytest.raises(NoExamples):
        pdst.indexes(
            elements=st.just,
            min_size=3, max_size=3, dtype=bool
        ).example()


@given(pdst.indexes(dtype=bool, unique=True))
def test_unique_indexes_of_small_values(ix):
    assert len(ix) <= 2
    assert len(set(ix)) == len(ix)


@given(st.data())
def test_generate_arbitrary_indices(data):
    min_size = data.draw(st.integers(0, 10), 'min_size')
    max_size = data.draw(
        st.none() | st.integers(min_size, min_size+10), 'max_size')
    unique = data.draw(st.booleans(), 'unique')
    allow_nan = data.draw(st.booleans(), 'allow_nan')
    order = data.draw(st.sampled_from((0, 1, -1)), 'order')
    dtype = data.draw(st.none() | npst.scalar_dtypes(), 'dtype')

    if dtype is not None:
        assume(supported_by_pandas(dtype))
        assume(order == 0 or is_ordered_dtype_for_index(dtype))

    base_dtype = np.dtype(int) if dtype is None else dtype

    non_default_elements = data.draw(st.booleans(), 'non_default_elements')

    if non_default_elements:
        def elements(i): return npst.from_dtype(base_dtype)
    else:
        elements = st.just

    index = data.draw(pdst.indexes(
        elements=elements, dtype=dtype, min_size=min_size, max_size=max_size,
        unique=unique, order=order, allow_nan=allow_nan
    ))

    if dtype is not None:
        inferred_dtype = pandas.Index([], dtype=dtype).dtype
    else:
        inferred_dtype = np.dtype(int)

    assert index.dtype == inferred_dtype

    has_nan = False
    for v in index.values:
        try:
            has_nan = np.isnan(float(v))
        except TypeError:
            pass
        if has_nan:
            break

    if has_nan:
        assert allow_nan
    else:
        if unique:
            assert len(set(index.values)) == len(index)
        if order > 0:
            assert list(index.values) == sorted(index.values)
        if order < 0:
            assert list(index.values) == sorted(index.values, reverse=True)
