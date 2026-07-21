# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import datetime as dt
import zoneinfo

import numpy as np
import pandas as pd
import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.extra import numpy as nps, pandas as pdst
from hypothesis.extra.pandas.impl import PANDAS_GE_21, IntegerDtype

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


TIMEZONES = [
    "UTC",
    dt.timezone.utc,
    dt.timezone(dt.timedelta(hours=5, minutes=30)),
    dt.timezone(dt.timedelta(hours=-8)),
]
requires_pandas21 = pytest.mark.skipif(
    not PANDAS_GE_21, reason="timezone-aware dtypes require pandas >= 2.1"
)


@pytest.mark.skipif(PANDAS_GE_21, reason="only raises on pandas < 2.1")
def test_tz_aware_dtype_requires_pandas_21():
    with pytest.raises(InvalidArgument, match=r"requires pandas >= 2\.1"):
        check_can_generate_examples(pdst.series(dtype="datetime64[ns, UTC]"))


@requires_pandas21
@pytest.mark.parametrize("unit", ["s", "ms", "us", "ns"])
@pytest.mark.parametrize("tz", TIMEZONES)
def test_tz_aware_series_share_one_timezone(unit, tz):
    dtype = pd.DatetimeTZDtype(unit=unit, tz=tz)
    assert_all_examples(
        pdst.series(dtype=dtype, index=pdst.range_indexes(min_size=1)),
        lambda s: s.dtype == dtype and (s.dt.tz == dtype.tz),
    )


@requires_pandas21
def test_tz_aware_series_from_string_dtype():
    assert_all_examples(
        pdst.series(dtype="datetime64[ns, UTC]"),
        lambda s: str(s.dtype) == "datetime64[ns, UTC]",
    )


@requires_pandas21
@given(pdst.series(dtype="datetime64[s, UTC]", index=pdst.range_indexes(max_size=0)))
def test_empty_tz_aware_series(s):
    assert len(s) == 0
    assert str(s.dtype) == "datetime64[s, UTC]"


@requires_pandas21
def test_ns_resolution_series_exercise_sub_microsecond_values():
    find_any(
        pdst.series(dtype="datetime64[ns, UTC]", index=pdst.range_indexes(min_size=1)),
        lambda s: (s.dt.nanosecond != 0).any(),
    )


@requires_pandas21
def test_second_resolution_covers_beyond_datetime_max():
    # The full representable range of datetime64[s] is vastly wider than
    # Python's datetime, which stops at the end of the year 9999.
    epoch = dt.datetime(1970, 1, 1)
    beyond_datetime_max = (dt.datetime.max - epoch).total_seconds() + 86400
    find_any(
        pdst.series(dtype="datetime64[s, UTC]", index=pdst.range_indexes(min_size=1)),
        lambda s: _utc_seconds(s.dropna()).map(abs).gt(beyond_datetime_max).any(),
    )


def _utc_seconds(s):
    return s.dt.tz_convert("UTC").dt.tz_localize(None).astype("int64")


@requires_pandas21
def test_tz_aware_series_accepts_custom_elements():
    tz = dt.timezone.utc
    elements = st.datetimes(timezones=st.just(tz)).map(lambda d: d.replace(year=2000))
    assert_all_examples(
        pdst.series(dtype=pd.DatetimeTZDtype("ns", tz), elements=elements),
        lambda s: (s.dt.year == 2000).all(),
    )


@requires_pandas21
def test_tz_aware_series_from_zoneinfo_timezone():
    dtype = pd.DatetimeTZDtype(unit="us", tz=zoneinfo.ZoneInfo("America/New_York"))
    assert_all_examples(
        pdst.series(dtype=dtype, index=pdst.range_indexes(min_size=1)),
        lambda s: s.dtype == dtype,
    )


@requires_pandas21
def test_variable_offset_timezones_stay_within_datetime_range():
    # Unlike fixed-offset timezones, zones whose UTC offset varies over time
    # resolve offsets through stdlib datetimes, so generated values must stay
    # within the years 1-9999 which those can represent.
    dtype = pd.DatetimeTZDtype(unit="s", tz=zoneinfo.ZoneInfo("America/New_York"))
    assert_all_examples(
        pdst.series(dtype=dtype, index=pdst.range_indexes(min_size=1)),
        lambda s: s.dropna().dt.year.between(1, 9999).all(),
    )


@requires_pandas21
def test_tz_aware_series_from_naive_datetime_elements():
    # Naive elements are interpreted as wall times in the dtype's timezone,
    # with the pandas constructor's handling of DST transitions: ambiguous
    # times resolve to the first occurrence, and imaginary times are shifted
    # out of the gap.  We bound the elements because pandas 2.1 localizes
    # python datetimes via nanoseconds, overflowing beyond that range.
    dtype = pd.DatetimeTZDtype("us", zoneinfo.ZoneInfo("America/New_York"))
    elements = st.datetimes(dt.datetime(1678, 1, 1), dt.datetime(2261, 12, 31))
    assert_all_examples(
        pdst.series(dtype=dtype, elements=elements),
        lambda s: s.dtype == dtype,
    )


@requires_pandas21
def test_tz_aware_series_ambiguous_times_resolve_by_fold():
    # 01:00-01:59 on 2020-11-01 occurs twice in this timezone; the fold of
    # each generated datetime selects which occurrence we mean, so both UTC
    # offsets should appear in generated series.
    tz = zoneinfo.ZoneInfo("America/New_York")
    strategy = pdst.series(
        dtype=pd.DatetimeTZDtype("us", tz),
        elements=st.datetimes(
            dt.datetime(2020, 11, 1, 1, 0),
            dt.datetime(2020, 11, 1, 1, 59),
            timezones=st.just(tz),
        ),
        index=pdst.range_indexes(min_size=1),
    )
    find_any(strategy, lambda s: (s.dt.strftime("%z") == "-0400").any())
    find_any(strategy, lambda s: (s.dt.strftime("%z") == "-0500").any())


@requires_pandas21
def test_tz_aware_series_imaginary_times_are_normalized():
    # 02:00-02:59 on 2020-03-08 does not exist in this timezone; such values
    # land on a real instant on one side of the DST gap, depending on fold.
    tz = zoneinfo.ZoneInfo("America/New_York")
    strategy = pdst.series(
        dtype=pd.DatetimeTZDtype("us", tz),
        elements=st.datetimes(
            dt.datetime(2020, 3, 8, 2, 0),
            dt.datetime(2020, 3, 8, 2, 59),
            timezones=st.just(tz),
        ),
        index=pdst.range_indexes(min_size=1),
    )
    assert_all_examples(strategy, lambda s: s.dt.hour.isin([1, 3]).all())


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
