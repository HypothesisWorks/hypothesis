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

import datetime as dt

import pytest
import pytz

from hypothesis import assume, given
from hypothesis.errors import InvalidArgument
from hypothesis.extra.pytz import timezones
from hypothesis.internal.compat import PY2
from hypothesis.strategies import datetimes, sampled_from, times
from tests.common.debug import assert_can_trigger_event, minimal


def test_utc_is_minimal():
    assert pytz.UTC is minimal(timezones())


def test_can_generate_non_naive_time():
    assert minimal(times(timezones=timezones()), lambda d: d.tzinfo).tzinfo == pytz.UTC


def test_can_generate_non_naive_datetime():
    assert (
        minimal(datetimes(timezones=timezones()), lambda d: d.tzinfo).tzinfo == pytz.UTC
    )


@given(datetimes(timezones=timezones()))
def test_timezone_aware_datetimes_are_timezone_aware(dt):
    assert dt.tzinfo is not None


@given(sampled_from(["min_value", "max_value"]), datetimes(timezones=timezones()))
def test_datetime_bounds_must_be_naive(name, val):
    with pytest.raises(InvalidArgument):
        datetimes(**{name: val}).validate()


def test_underflow_in_simplify():
    # we shouldn't trigger a pytz bug when we're simplifying
    minimal(
        datetimes(
            max_value=dt.datetime.min + dt.timedelta(days=3), timezones=timezones()
        ),
        lambda x: x.tzinfo != pytz.UTC,
    )


def test_overflow_in_simplify():
    # we shouldn't trigger a pytz bug when we're simplifying
    minimal(
        datetimes(
            min_value=dt.datetime.max - dt.timedelta(days=3), timezones=timezones()
        ),
        lambda x: x.tzinfo != pytz.UTC,
    )


def test_timezones_arg_to_datetimes_must_be_search_strategy():
    with pytest.raises(InvalidArgument):
        datetimes(timezones=pytz.all_timezones).validate()
    with pytest.raises(InvalidArgument):
        tz = [pytz.timezone(t) for t in pytz.all_timezones]
        datetimes(timezones=tz).validate()


@given(times(timezones=timezones()))
def test_timezone_aware_times_are_timezone_aware(dt):
    assert dt.tzinfo is not None


def test_can_generate_non_utc():
    times(timezones=timezones()).filter(
        lambda d: assume(d.tzinfo) and d.tzinfo.zone != u"UTC"
    ).validate()


@given(sampled_from(["min_value", "max_value"]), times(timezones=timezones()))
def test_time_bounds_must_be_naive(name, val):
    with pytest.raises(InvalidArgument):
        times(**{name: val}).validate()


@pytest.mark.skipif(
    PY2,
    reason="""This test fails mysteriously on Python 2 and
between its impending deprecation and the nicheness of the test it's not
really worth debugging it.""",
)
def test_can_trigger_error_in_draw_near_max_date():
    assert_can_trigger_event(
        datetimes(
            min_value=dt.datetime.max - dt.timedelta(days=3), timezones=timezones()
        ),
        lambda event: "Failed to draw a datetime" in event,
    )
