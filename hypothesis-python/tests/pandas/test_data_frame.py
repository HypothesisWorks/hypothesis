# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import numpy as np

import hypothesis.extra.numpy as npst
import hypothesis.extra.pandas as pdst
import hypothesis.strategies as st
from hypothesis import HealthCheck, given, reject, settings
from tests.common.debug import find_any
from tests.pandas.helpers import supported_by_pandas


@given(pdst.data_frames([pdst.column("a", dtype=int), pdst.column("b", dtype=float)]))
def test_can_have_columns_of_distinct_types(df):
    assert df["a"].dtype == np.dtype(int)
    assert df["b"].dtype == np.dtype(float)


@given(
    pdst.data_frames(
        [pdst.column(dtype=int)], index=pdst.range_indexes(min_size=1, max_size=5)
    )
)
def test_respects_size_bounds(df):
    assert 1 <= len(df) <= 5


@given(pdst.data_frames(pdst.columns(["A", "B"], dtype=float)))
def test_can_specify_just_column_names(df):
    df["A"]
    df["B"]


@given(pdst.data_frames(pdst.columns(2, dtype=float)))
def test_can_specify_just_column_count(df):
    df[0]
    df[1]


@given(
    pdst.data_frames(
        rows=st.fixed_dictionaries({"A": st.integers(1, 10), "B": st.floats()})
    )
)
def test_gets_the_correct_data_shape_for_just_rows(table):
    assert table["A"].dtype == np.dtype("int64")
    assert table["B"].dtype == np.dtype(float)


@given(
    pdst.data_frames(
        columns=pdst.columns(["A", "B"], dtype=int),
        rows=st.lists(st.integers(0, 1000), min_size=2, max_size=2).map(sorted),
    )
)
def test_can_specify_both_rows_and_columns_list(d):
    assert d["A"].dtype == np.dtype(int)
    assert d["B"].dtype == np.dtype(int)
    for _, r in d.iterrows():
        assert r["A"] <= r["B"]


@given(
    pdst.data_frames(
        columns=pdst.columns(["A", "B"], dtype=int),
        rows=st.lists(st.integers(0, 1000), min_size=2, max_size=2)
        .map(sorted)
        .map(tuple),
    )
)
def test_can_specify_both_rows_and_columns_tuple(d):
    assert d["A"].dtype == np.dtype(int)
    assert d["B"].dtype == np.dtype(int)
    for _, r in d.iterrows():
        assert r["A"] <= r["B"]


@given(
    pdst.data_frames(
        columns=pdst.columns(["A", "B"], dtype=int),
        rows=st.lists(st.integers(0, 1000), min_size=2, max_size=2).map(
            lambda x: {"A": min(x), "B": max(x)}
        ),
    )
)
def test_can_specify_both_rows_and_columns_dict(d):
    assert d["A"].dtype == np.dtype(int)
    assert d["B"].dtype == np.dtype(int)
    for _, r in d.iterrows():
        assert r["A"] <= r["B"]


@given(
    pdst.data_frames(
        [
            pdst.column(
                "A",
                fill=st.just(float("nan")),
                dtype=float,
                elements=st.floats(allow_nan=False),
            )
        ],
        rows=st.builds(dict),
    )
)
def test_can_fill_in_missing_elements_from_dict(df):
    assert np.isnan(df["A"]).all()


@st.composite
def column_strategy(draw):
    name = draw(st.none() | st.text())
    dtype = draw(npst.scalar_dtypes().filter(supported_by_pandas))
    pass_dtype = not draw(st.booleans())
    if pass_dtype:
        pass_elements = not draw(st.booleans())
    else:
        pass_elements = True
    if pass_elements:
        elements = npst.from_dtype(dtype)
    else:
        elements = None

    unique = draw(st.booleans())
    fill = st.nothing() if draw(st.booleans()) else None

    return pdst.column(
        name=name, dtype=dtype, unique=unique, fill=fill, elements=elements
    )


@given(pdst.data_frames(pdst.columns(1, dtype=np.dtype("<M8[ns]"))))
def test_data_frames_with_timestamp_columns(df):
    pass


@given(
    pdst.data_frames(
        pdst.columns(["A"], dtype=float, fill=st.just(float("nan")), unique=True)
    )
)
def test_unique_column_with_fill(df):
    assert len(set(df["A"])) == len(df["A"])


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(st.data())
def test_arbitrary_data_frames(data):
    columns = data.draw(
        st.lists(
            column_strategy(),
            unique_by=lambda c: c.name if c.name is not None else float("nan"),
        )
    )

    try:
        # Use raw data to work around pandas bug in repr. See
        # https://github.com/pandas-dev/pandas/issues/27484
        df = data.conjecture_data.draw(pdst.data_frames(columns))
    except Exception as e:
        if type(e).__name__ == "OutOfBoundsDatetime":
            # See https://github.com/HypothesisWorks/hypothesis-python/pull/826
            reject()
        else:
            raise
    data_frame_columns = list(df)

    assert len(data_frame_columns) == len(columns)

    for i, (c, n) in enumerate(zip(columns, df)):
        if c.name is None:
            assert n == i
        else:
            assert c.name == n

    for i, c in enumerate(columns):
        column_name = data_frame_columns[i]
        values = df[column_name]
        if c.unique:
            assert len(set(values)) == len(values)


@given(
    pdst.data_frames(
        pdst.columns(["A"], unique=True, dtype=int), rows=st.tuples(st.integers(0, 10))
    )
)
def test_can_specify_unique_with_rows(df):
    column = df["A"]
    assert len(set(column)) == len(column)


def test_uniqueness_does_not_affect_other_rows_1():
    data_frames = pdst.data_frames(
        [
            pdst.column("A", dtype=int, unique=True),
            pdst.column("B", dtype=int, unique=False),
        ],
        rows=st.tuples(st.integers(0, 10), st.integers(0, 10)),
        index=pdst.range_indexes(2, 2),
    )
    find_any(data_frames, lambda x: x["B"][0] == x["B"][1])


def test_uniqueness_does_not_affect_other_rows_2():
    data_frames = pdst.data_frames(
        [
            pdst.column("A", dtype=bool, unique=False),
            pdst.column("B", dtype=int, unique=True),
        ],
        rows=st.tuples(st.booleans(), st.integers(0, 10)),
        index=pdst.range_indexes(2, 2),
    )
    find_any(data_frames, lambda x: x["A"][0] == x["A"][1])


@given(
    pdst.data_frames(pdst.columns(["A"], dtype=int, fill=st.just(7)), rows=st.tuples())
)
def test_will_fill_missing_columns_in_tuple_row(df):
    for d in df["A"]:
        assert d == 7


@settings(suppress_health_check=[HealthCheck.filter_too_much])
@given(
    pdst.data_frames(
        index=pdst.range_indexes(10, 10),
        columns=[pdst.column(elements=st.integers(0, 9), fill=None, unique=True)],
    )
)
def test_can_generate_unique_columns(df):
    assert set(df[0]) == set(range(10))
