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
import sys
import warnings

import pytest

from hypothesis import assume, given
from hypothesis.errors import FailedHealthCheck, InvalidArgument
from hypothesis.strategies import data, datetimes, just, sampled_from, times
from hypothesis.strategies._internal.datetime import datetime_does_not_exist

from tests.common.debug import assert_all_examples, find_any, minimal
from tests.common.utils import fails_with

with warnings.catch_warnings():
    if sys.version_info[:2] >= (3, 12):
        # Prior to https://github.com/dateutil/dateutil/pull/1285/
        warnings.simplefilter("ignore", DeprecationWarning)
    from dateutil import tz, zoneinfo

from hypothesis.extra.dateutil import timezones


def test_utc_is_minimal():
    assert tz.UTC is minimal(timezones())


def test_can_generate_non_naive_time():
    assert minimal(times(timezones=timezones()), lambda d: d.tzinfo).tzinfo == tz.UTC


def test_can_generate_non_naive_datetime():
    assert (
        minimal(datetimes(timezones=timezones()), lambda d: d.tzinfo).tzinfo == tz.UTC
    )


@given(datetimes(timezones=timezones()))
def test_timezone_aware_datetimes_are_timezone_aware(dt):
    assert dt.tzinfo is not None


@given(sampled_from(["min_value", "max_value"]), datetimes(timezones=timezones()))
def test_datetime_bounds_must_be_naive(name, val):
    with pytest.raises(InvalidArgument):
        datetimes(**{name: val}).validate()


def test_timezones_arg_to_datetimes_must_be_search_strategy():
    all_timezones = zoneinfo.get_zonefile_instance().zones
    with pytest.raises(InvalidArgument):
        datetimes(timezones=all_timezones).validate()


@given(times(timezones=timezones()))
def test_timezone_aware_times_are_timezone_aware(dt):
    assert dt.tzinfo is not None


def test_can_generate_non_utc():
    times(timezones=timezones()).filter(
        lambda d: assume(d.tzinfo) and d.tzinfo.zone != "UTC"
    ).validate()


@given(sampled_from(["min_value", "max_value"]), times(timezones=timezones()))
def test_time_bounds_must_be_naive(name, val):
    with pytest.raises(InvalidArgument):
        times(**{name: val}).validate()


def test_should_have_correct_ordering():
    def offset(timezone):
        return abs(timezone.utcoffset(dt.datetime(2000, 1, 1)))

    next_interesting_tz = minimal(timezones(), lambda tz: offset(tz) > dt.timedelta(0))
    assert offset(next_interesting_tz) == dt.timedelta(seconds=3600)


@given(data(), datetimes(), datetimes())
def test_datetimes_stay_within_naive_bounds(data, lo, hi):
    if lo > hi:
        lo, hi = hi, lo
    out = data.draw(datetimes(lo, hi, timezones=timezones()))
    assert lo <= out.replace(tzinfo=None) <= hi


DAY_WITH_IMAGINARY_HOUR_KWARGS = {
    # The day of a spring-forward transition; 2am is imaginary
    "min_value": dt.datetime(2020, 10, 4),
    "max_value": dt.datetime(2020, 10, 5),
    "timezones": just(tz.gettz("Australia/Sydney")),
}


@given(datetimes(timezones=timezones()) | datetimes(**DAY_WITH_IMAGINARY_HOUR_KWARGS))
def test_dateutil_exists_our_not_exists_are_inverse(value):
    assert datetime_does_not_exist(value) == (not tz.datetime_exists(value))


def test_datetimes_can_exclude_imaginary():
    find_any(
        datetimes(**DAY_WITH_IMAGINARY_HOUR_KWARGS, allow_imaginary=True),
        lambda x: not tz.datetime_exists(x),
    )
    assert_all_examples(
        datetimes(**DAY_WITH_IMAGINARY_HOUR_KWARGS, allow_imaginary=False),
        tz.datetime_exists,
    )


@fails_with(FailedHealthCheck)
@given(
    datetimes(
        max_value=dt.datetime(1, 1, 1, 9),
        timezones=just(tz.gettz("Australia/Sydney")),
        allow_imaginary=False,
    )
)
def test_non_imaginary_datetimes_at_boundary(val):
    # This is expected to fail because Australia/Sydney is UTC+10,
    # and the filter logic overflows when checking for round-trips.
    raise AssertionError
