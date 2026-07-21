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
from calendar import monthrange

import pytest

from hypothesis import HealthCheck, example, given, settings, strategies as st
from hypothesis.errors import InvalidArgument, Unsatisfiable
from hypothesis.strategies import dates, datetimes, timedeltas, times
from hypothesis.strategies._internal.datetime import _instant, _num_days_in_month

from tests.common.debug import (
    assert_all_examples,
    assert_simple_property,
    check_can_generate_examples,
    find_any,
    minimal,
)


@example(1900)
@example(2000)
@example(2004)
@example(2100)
@given(st.integers(dt.MINYEAR, dt.MAXYEAR))
def test_num_days_in_month_matches_monthrange(year):
    for month in range(1, 13):
        assert _num_days_in_month(year, month) == monthrange(year, month)[1]


def test_can_find_positive_delta():
    assert minimal(timedeltas(), lambda x: x.days > 0) == dt.timedelta(1)


def test_can_find_negative_delta():
    assert minimal(
        timedeltas(max_value=dt.timedelta(10**6)), lambda x: x.days < 0
    ) == dt.timedelta(-1)


def test_can_find_on_the_second():
    find_any(timedeltas(), lambda x: x.seconds == 0)


def test_can_find_off_the_second():
    find_any(timedeltas(), lambda x: x.seconds != 0)


def test_simplifies_towards_zero_delta():
    d = minimal(timedeltas())
    assert d.days == d.seconds == d.microseconds == 0


def test_min_value_is_respected():
    assert minimal(timedeltas(min_value=dt.timedelta(days=10))).days == 10


def test_max_value_is_respected():
    assert minimal(timedeltas(max_value=dt.timedelta(days=-10))).days == -10


@settings(suppress_health_check=list(HealthCheck))
@given(timedeltas())
def test_single_timedelta(val):
    assert_simple_property(timedeltas(val, val), lambda v: v is val)


def test_simplifies_towards_millenium():
    d = minimal(datetimes())
    assert d.year == 2000
    assert d.month == d.day == 1
    assert d.hour == d.minute == d.second == d.microsecond == 0


@given(datetimes())
def test_default_datetimes_are_naive(dt):
    assert dt.tzinfo is None


def test_bordering_on_a_leap_year():
    x = minimal(
        datetimes(
            dt.datetime.min.replace(year=2003), dt.datetime.max.replace(year=2005)
        ),
        lambda x: x.month == 2 and x.day == 29,
        settings=settings(max_examples=2500),
    )
    assert x.year == 2004


def test_can_find_after_the_year_2000():
    assert minimal(dates(), lambda x: x.year > 2000).year == 2001


def test_can_find_before_the_year_2000():
    assert minimal(dates(), lambda x: x.year < 2000).year == 1999


@pytest.mark.parametrize("month", range(1, 13))
def test_can_find_each_month(month):
    find_any(dates(), lambda x: x.month == month, settings(max_examples=10**6))


def test_min_year_is_respected():
    assert minimal(dates(min_value=dt.date.min.replace(2003))).year == 2003


def test_max_year_is_respected():
    assert minimal(dates(max_value=dt.date.min.replace(1998))).year == 1998


@given(dates())
def test_single_date(val):
    assert find_any(dates(val, val)) is val


def test_can_find_midnight():
    find_any(times(), lambda x: x.hour == x.minute == x.second == 0)


def test_can_find_non_midnight():
    assert minimal(times(), lambda x: x.hour != 0).hour == 1


def test_can_find_on_the_minute():
    find_any(times(), lambda x: x.second == 0)


def test_can_find_off_the_minute():
    find_any(times(), lambda x: x.second != 0)


def test_simplifies_towards_midnight():
    d = minimal(times())
    assert d.hour == d.minute == d.second == d.microsecond == 0


def test_can_generate_naive_time():
    find_any(times(), lambda d: not d.tzinfo)


@given(times())
def test_naive_times_are_naive(dt):
    assert dt.tzinfo is None


def test_can_generate_datetime_with_fold_1():
    find_any(datetimes(), lambda d: d.fold)


def test_can_generate_time_with_fold_1():
    find_any(times(), lambda d: d.fold)


@given(datetimes(allow_imaginary=False))
def test_allow_imaginary_is_not_an_error_for_naive_datetimes(d):
    pass


UTC = dt.timezone.utc
fixed_offsets = st.builds(
    dt.timezone, st.timedeltas(dt.timedelta(hours=-23), dt.timedelta(hours=23))
)


@pytest.mark.parametrize("aware_arg", ["min_value", "max_value"])
def test_mixing_aware_and_naive_bounds_is_invalid(aware_arg):
    kwargs = {
        "min_value": dt.datetime(2000, 1, 1),
        "max_value": dt.datetime(2001, 1, 1),
    }
    kwargs[aware_arg] = kwargs[aware_arg].replace(tzinfo=UTC)
    with pytest.raises(InvalidArgument):
        datetimes(**kwargs).validate()


def test_aware_bounds_are_compared_as_moments_in_time():
    lo = dt.datetime(2000, 1, 1, 12, tzinfo=UTC)
    hi = lo.astimezone(dt.timezone(dt.timedelta(hours=-5)))  # the same moment
    assert lo.replace(tzinfo=None) > hi.replace(tzinfo=None)
    assert_simple_property(datetimes(lo, hi, timezones=st.just(UTC)), lambda d: d == lo)
    with pytest.raises(InvalidArgument):
        datetimes(hi + dt.timedelta(seconds=1), lo, timezones=st.just(UTC)).validate()


def test_aware_bounds_with_none_from_timezones_strategy_is_invalid():
    lo = dt.datetime(2000, 1, 1, tzinfo=UTC)
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(datetimes(min_value=lo, timezones=st.none()))


@given(
    st.data(),
    datetimes(timezones=st.just(UTC)),
    datetimes(timezones=st.just(UTC)),
)
def test_datetimes_stay_within_aware_bounds(data, lo, hi):
    if lo > hi:
        lo, hi = hi, lo
    out = data.draw(datetimes(lo, hi, timezones=fixed_offsets))
    assert isinstance(out.tzinfo, dt.timezone)
    assert _instant(lo) <= _instant(out) <= _instant(hi)


@given(datetimes(min_value=dt.datetime(2000, 1, 1, tzinfo=UTC), timezones=st.just(UTC)))
def test_single_aware_bound_min(d):
    assert d >= dt.datetime(2000, 1, 1, tzinfo=UTC)


@given(datetimes(max_value=dt.datetime(2000, 1, 1, tzinfo=UTC), timezones=st.just(UTC)))
def test_single_aware_bound_max(d):
    assert d <= dt.datetime(2000, 1, 1, tzinfo=UTC)


def test_shrinks_to_aware_min_bound():
    lo = dt.datetime(2024, 3, 4, 5, 6, tzinfo=UTC)
    assert minimal(datetimes(min_value=lo, timezones=st.just(UTC))) == lo


def test_bounds_unrepresentable_in_timezone_are_rejected():
    lo = dt.datetime.max.replace(tzinfo=UTC) - dt.timedelta(hours=1)
    tz = dt.timezone(dt.timedelta(hours=5))
    with pytest.raises(Unsatisfiable):
        check_can_generate_examples(datetimes(min_value=lo, timezones=st.just(tz)))


@given(
    datetimes(
        dt.datetime.min.replace(tzinfo=UTC),
        dt.datetime.max.replace(tzinfo=UTC),
        timezones=st.sampled_from(
            [dt.timezone(dt.timedelta(hours=h)) for h in (-10, 10)]
        ),
    )
)
def test_extreme_aware_bounds_are_clamped_per_timezone(d):
    # Each of these timezones can represent only some moments between the
    # bounds; the rest of each bound's range is clamped away harmlessly.
    pass


class EternalFold(dt.tzinfo):
    """A pathological timezone in which every wall time is ambiguous, with a
    utcoffset of +2h at fold=0 and +1h at fold=1."""

    def utcoffset(self, value):
        return dt.timedelta(hours=2 - value.fold)

    def tzname(self, value):
        return "Weird"

    def dst(self, value):
        return dt.timedelta(0)


def test_pathological_timezone_may_leave_no_valid_fold():
    # With an interval of more than a day we draw local wall times; every wall
    # time in EternalFold is ambiguous, so draws adjacent to a bound whose fold
    # would fall out of bounds are rejected.
    tz = EternalFold()
    lo = dt.datetime(2000, 1, 1, 1, 10, fold=1, tzinfo=tz)
    hi = dt.datetime(2000, 1, 3, 2, 20, tzinfo=tz)
    assert_all_examples(
        datetimes(lo, hi, timezones=st.just(tz)),
        lambda d: _instant(lo) <= _instant(d) <= _instant(hi),
        settings=settings(max_examples=300),
    )


def test_pathological_timezone_inverted_bounds_draw_via_utc():
    tz = EternalFold()
    lo = dt.datetime(2000, 1, 1, 2, 0, tzinfo=tz)
    hi = dt.datetime(2000, 1, 1, 1, 30, fold=1, tzinfo=tz)
    # ...so lo is an earlier moment than hi, but a later wall-clock time!
    assert _instant(lo) < _instant(hi)
    assert lo.replace(tzinfo=None) > hi.replace(tzinfo=None)
    assert_all_examples(
        datetimes(lo, hi, timezones=st.just(tz)),
        lambda d: _instant(lo) <= _instant(d) <= _instant(hi),
    )


def test_pathological_timezone_bounds_unrepresentable_in_utc():
    # Wall-clock-inverted bounds near datetime.min, whose moments precede it.
    tz = EternalFold()
    lo = dt.datetime.min.replace(minute=30, tzinfo=tz)
    hi = dt.datetime.min.replace(minute=15, fold=1, tzinfo=tz)
    assert _instant(lo) < _instant(hi)
    with pytest.raises(Unsatisfiable):
        check_can_generate_examples(datetimes(lo, hi, timezones=st.just(tz)))


def test_pathological_timezone_unrepresentable_moments_are_rejected():
    # Near datetime.max, some of the moments between these bounds have no
    # EternalFold wall time at all; drawing one is rejected, and the rest
    # generate as usual.
    tz = EternalFold()
    lo = dt.datetime.max.replace(hour=23, minute=30, tzinfo=tz)
    hi = dt.datetime.max.replace(hour=23, minute=59, fold=1, tzinfo=tz)
    assert_all_examples(
        datetimes(lo, hi, timezones=st.just(tz)),
        lambda d: _instant(lo) <= _instant(d) <= _instant(hi),
    )


def test_pathological_timezone_single_bound_near_extreme():
    tz = EternalFold()
    hi = (dt.datetime.min + dt.timedelta(minutes=90)).replace(fold=1, tzinfo=tz)
    assert_all_examples(
        datetimes(max_value=hi, timezones=st.just(tz)),
        lambda d: _instant(d) <= _instant(hi),
    )
