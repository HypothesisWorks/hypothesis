# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import datetime as dt

import pytest
from dateutil import tz, zoneinfo

from hypothesis import assume, given
from hypothesis.errors import InvalidArgument
from hypothesis.extra.dateutil import timezones
from hypothesis.strategies import datetimes, sampled_from, times
from tests.common.debug import minimal


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
