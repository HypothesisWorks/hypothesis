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

from hypothesis import given, settings, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.extra import numpy as nps, pandas as pdst
from hypothesis.extra.pandas.impl import IntegerDtype

from tests.common.debug import (
    assert_all_examples,
    assert_no_examples,
    check_can_generate_examples,
    find_any,
)
from tests.pandas.helpers import supported_by_pandas


@given(st.data())
def test_can_create_a_series_of_any_dtype(data):
    dtype = data.draw(nps.scalar_dtypes().filter(supported_by_pandas))
    # Use raw data to work around pandas bug in repr. See
    # https://github.com/pandas-dev/pandas/issues/27484
    series = data.conjecture_data.draw(pdst.series(dtype=dtype))
    assert series.dtype == dtype


@given(pdst.series(dtype=object))
def test_can_create_a_series_of_object_python_type(series):
    assert series.dtype == np.dtype("O")


@given(
    pdst.series(
        elements=nps.arrays(
            nps.array_dtypes() | nps.scalar_dtypes(),
            nps.array_shapes(),
        ),
        dtype=object,
    )
)
@settings(max_examples=5)
def test_object_series_are_of_type_object(series):
    assert series.dtype == np.dtype("O")


def test_class_instances_not_allowed_in_scalar_series():
    class A:
        pass

    with pytest.raises(InvalidArgument):
        check_can_generate_examples(
            pdst.series(elements=st.just(A()), dtype=np.dtype("int"))
        )


def test_object_series_with_mixed_elements_still_has_object_dtype():
    class A:
        pass

    s = nps.arrays(
        np.dtype("O"),
        shape=nps.array_shapes(),
        elements=st.just(A()) | st.integers(),
    )

    assert_all_examples(s, lambda arr: arr.dtype == np.dtype("O"))
    find_any(s, lambda arr: len({type(x) for x in arr.ravel()}) > 1)


@given(st.data())
@settings(max_examples=10)
def test_series_can_hold_arbitrary_class_instances(data):
    instance = data.draw(st.from_type(type).flatmap(st.from_type))
    s = pdst.series(elements=st.just(instance), dtype=object)
    series = data.draw(s)

    assert all(v is instance for v in series.values)


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
