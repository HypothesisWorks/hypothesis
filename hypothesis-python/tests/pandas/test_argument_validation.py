# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re
from datetime import datetime, timedelta

import pandas as pd
import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.extra import pandas as pdst
from hypothesis.extra.pandas.impl import IntegerDtype

from tests.common.arguments import argument_validation_test, e
from tests.common.debug import check_can_generate_examples, find_any
from tests.common.utils import checks_deprecated_behaviour

BAD_ARGS = [
    e(pdst.data_frames),
    e(pdst.data_frames, pdst.columns(1, dtype="not a dtype")),
    e(pdst.data_frames, pdst.columns(1, elements="not a strategy")),
    e(pdst.data_frames, pdst.columns([[]])),
    e(pdst.data_frames, [], index=[]),
    e(pdst.data_frames, [], rows=st.fixed_dictionaries({"A": st.just(1)})),
    e(pdst.data_frames, pdst.columns(1)),
    e(pdst.data_frames, pdst.columns(1, dtype=float, fill=1)),
    e(pdst.data_frames, pdst.columns(1, dtype=float, elements=1)),
    e(pdst.data_frames, pdst.columns(1, fill=1, dtype=float)),
    e(pdst.data_frames, pdst.columns(["A", "A"], dtype=float)),
    pytest.param(
        *e(pdst.data_frames, pdst.columns(1, elements=st.none(), dtype=int)),
        marks=pytest.mark.skipif(IntegerDtype, reason="works with integer NA"),
    ),
    e(pdst.data_frames, pdst.columns(1, elements=st.text(), dtype=int)),
    e(pdst.data_frames, 1),
    e(pdst.data_frames, [1]),
    e(pdst.data_frames, pdst.columns(1, dtype="category")),
    e(
        pdst.data_frames,
        pdst.columns(["A"], dtype=bool),
        rows=st.tuples(st.booleans(), st.booleans()),
    ),
    e(
        pdst.data_frames,
        pdst.columns(1, elements=st.booleans()),
        rows=st.tuples(st.booleans()),
    ),
    e(pdst.data_frames, rows=st.integers(), index=pdst.range_indexes(0, 0)),
    e(pdst.data_frames, rows=st.integers(), index=pdst.range_indexes(1, 1)),
    e(pdst.data_frames, pdst.columns(1, dtype=int), rows=st.integers()),
    e(
        pdst.data_frames,
        columns=pdst.columns(["a", "b"], dtype=str, elements=st.text()),
        rows=st.just({"a": "x"}),
        index=pdst.indexes(dtype=int, min_size=1),
    ),
    e(
        pdst.data_frames,
        columns=pdst.columns(["a", "b"], dtype=str, elements=st.text()),
        rows=st.just(["x"]),
        index=pdst.indexes(dtype=int, min_size=1),
    ),
    e(pdst.indexes),
    e(pdst.indexes, dtype="category"),
    e(pdst.indexes, dtype="not a dtype"),
    e(pdst.indexes, elements="not a strategy"),
    e(pdst.indexes, elements=st.text(), dtype=float),
    pytest.param(
        *e(pdst.indexes, elements=st.none(), dtype=int),
        marks=pytest.mark.skipif(IntegerDtype, reason="works with integer NA"),
    ),
    e(pdst.indexes, elements=st.text(), dtype=int),
    e(pdst.indexes, elements=st.integers(0, 10), dtype=st.sampled_from([int, float])),
    e(pdst.indexes, dtype=int, max_size=0, min_size=1),
    e(pdst.indexes, dtype=int, unique="true"),
    e(pdst.indexes, dtype=int, min_size="0"),
    e(pdst.indexes, dtype=int, max_size="1"),
    e(pdst.range_indexes, 1, 0),
    e(pdst.range_indexes, min_size="0"),
    e(pdst.range_indexes, max_size="1"),
    e(pdst.range_indexes, name=""),
    e(pdst.series),
    e(pdst.series, dtype="not a dtype"),
    e(pdst.series, elements="not a strategy"),
    pytest.param(
        *e(pdst.series, elements=st.none(), dtype=int),
        marks=pytest.mark.skipif(IntegerDtype, reason="works with integer NA"),
    ),
    e(pdst.series, elements=st.text(), dtype=int),
    e(pdst.series, dtype="category"),
    e(pdst.series, index="not a strategy"),
]


test_raise_invalid_argument = argument_validation_test(BAD_ARGS)

lo, hi = pd.Timestamp(2017, 1, 1), pd.Timestamp(2084, 12, 21)


@given(st.datetimes(min_value=lo, max_value=hi))
def test_timestamp_as_datetime_bounds(dt):
    # Would have caught https://github.com/HypothesisWorks/hypothesis/issues/2406
    assert isinstance(dt, datetime)
    assert lo <= dt <= hi
    assert not isinstance(dt, pd.Timestamp)


@checks_deprecated_behaviour
def test_confusing_object_dtype_aliases():
    check_can_generate_examples(
        pdst.series(elements=st.tuples(st.integers()), dtype=tuple)
    )


@pytest.mark.skipif(
    not IntegerDtype, reason="Nullable types not available in this version of Pandas"
)
def test_pandas_nullable_types_class():
    st = pdst.series(dtype=pd.core.arrays.integer.Int8Dtype)
    with pytest.raises(
        InvalidArgument, match="Otherwise it would be treated as dtype=object"
    ):
        find_any(st, lambda s: s.isna().any())


@pytest.mark.parametrize(
    "dtype_,expected_unit",
    [
        (datetime, "datetime64[ns]"),
        (pd.Timestamp, "datetime64[ns]"),
        (timedelta, "timedelta64[ns]"),
        (pd.Timedelta, "timedelta64[ns]"),
    ],
)
def test_invalid_datetime_or_timedelta_dtype_raises_error(dtype_, expected_unit):
    with pytest.raises(InvalidArgument, match=re.escape(expected_unit)):
        check_can_generate_examples(pdst.series(dtype=dtype_))
