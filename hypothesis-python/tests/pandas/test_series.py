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
import pandas as pd
import pytest

from hypothesis import assume, given, strategies as st
from hypothesis.extra import numpy as npst, pandas as pdst
from hypothesis.extra.pandas.impl import IntegerDtype

from tests.common.debug import assert_all_examples, assert_no_examples, find_any
from tests.pandas.helpers import supported_by_pandas


@given(st.data())
def test_can_create_a_series_of_any_dtype(data):
    dtype = np.dtype(data.draw(npst.scalar_dtypes()))
    assume(supported_by_pandas(dtype))
    # Use raw data to work around pandas bug in repr. See
    # https://github.com/pandas-dev/pandas/issues/27484
    series = data.conjecture_data.draw(pdst.series(dtype=dtype))
    assert series.dtype == pd.Series([], dtype=dtype).dtype


@given(pdst.series(dtype=float, index=pdst.range_indexes(min_size=2, max_size=5)))
def test_series_respects_size_bounds(s):
    assert 2 <= len(s) <= 5


def test_can_fill_series():
    nan_backed = pdst.series(elements=st.floats(allow_nan=False), fill=st.just(np.nan))
    find_any(nan_backed, lambda x: np.isnan(x).any())


@given(pdst.series(dtype=int))
def test_can_generate_integral_series(s):
    assert s.dtype == np.dtype(int)


@given(pdst.series(elements=st.integers(0, 10)))
def test_will_use_dtype_of_elements(s):
    assert s.dtype == np.dtype("int64")


@given(pdst.series(elements=st.floats(allow_nan=False)))
def test_will_use_a_provided_elements_strategy(s):
    assert not np.isnan(s).any()


@given(pdst.series(dtype="int8", unique=True))
def test_unique_series_are_unique(s):
    assert len(s) == len(set(s))


@given(pdst.series(dtype="int8", name=st.just("test_name")))
def test_name_passed_on(s):
    assert s.name == "test_name"


@pytest.mark.skipif(
    not IntegerDtype, reason="Nullable types not available in this version of Pandas"
)
@pytest.mark.parametrize(
    "dtype", ["Int8", pd.core.arrays.integer.Int8Dtype() if IntegerDtype else None]
)
def test_pandas_nullable_types(dtype):
    assert_no_examples(
        pdst.series(dtype=dtype, elements=st.just(0)),
        lambda s: s.isna().any(),
    )
    assert_all_examples(
        pdst.series(dtype=dtype, elements=st.none()),
        lambda s: s.isna().all(),
    )
    find_any(pdst.series(dtype=dtype), lambda s: not s.isna().any())
    e = find_any(pdst.series(dtype=dtype), lambda s: s.isna().any())
    assert type(e.dtype) == pd.core.arrays.integer.Int8Dtype
