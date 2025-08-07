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
from hypothesis.errors import InvalidArgument
from hypothesis.extra import numpy as npst, pandas as pdst
from hypothesis.extra.pandas.impl import IntegerDtype
from tests.common.debug import assert_all_examples, assert_no_examples, find_any
from tests.pandas.helpers import supported_by_pandas, dataclass_instance, all_elements, all_numpy_dtype_elements, \
    all_scalar_object_elements


@given(st.data())
def test_can_create_a_series_of_any_dtype(data):
    dtype = np.dtype(data.draw(npst.scalar_dtypes()))
    assume(supported_by_pandas(dtype))
    # Use raw data to work around pandas bug in repr. See
    # https://github.com/pandas-dev/pandas/issues/27484
    series = data.conjecture_data.draw(pdst.series(dtype=dtype))
    assert series.dtype == pd.Series([], dtype=dtype).dtype


@given(pdst.series(dtype=object))
def test_can_create_a_series_of_object_python_type(series):
    assert series.dtype == pd.Series([], dtype=object).dtype


def test_error_with_object_elements_in_numpy_dtype_arrays():
    with pytest.raises(InvalidArgument):
        find_any(
            pdst.series(elements=all_scalar_object_elements, dtype=all_numpy_dtype_elements)
        )


def test_can_generate_object_arrays_with_mixed_dtype_elements():
    find_any(pdst.series(elements=all_elements, dtype=object), lambda s: len({type(x) for x in s.values}) > 1)


@given(pdst.series(elements=st.just(dataclass_instance), dtype=object))
def test_can_hold_arbitrary_dataclass(series):
    assert all(x is dataclass_instance for x in series.values)


def test_series_is_still_object_dtype_even_with_numpy_types():
    assert_no_examples(
        pdst.series(elements=all_numpy_dtype_elements, dtype=object),
        lambda s: all(isinstance(e, np.dtype) for e in s.values) and (s.dtype != np.dtype('O'))
    )


@given(st.data(), all_elements)
def test_can_create_a_series_of_single_python_type(data, obj):
    # Ensure that arbitrary objects are present in the series without
    # modification.
    series = data.draw(
        pdst.series(
            elements=st.just(obj),
            index=pdst.range_indexes(min_size=1),
            dtype=object,
        )
    )
    assert all(val is obj for val in series.values)


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
