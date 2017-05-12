# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import datetime as dt

import pytz
import pytest

from hypothesis import given, assume
from hypothesis.errors import InvalidArgument
from tests.common.debug import minimal
from hypothesis.extra.pytz import timezones
from hypothesis.strategies import times, datetimes, sampled_from
from hypothesis.strategytests import strategy_test_suite

TestStandardDescriptorFeatures1 = strategy_test_suite(timezones())
TestStandardDescriptorFeatures_datetimes2 = strategy_test_suite(
    datetimes(timezones=timezones()))


def test_utc_is_minimal():
    assert pytz.UTC is minimal(timezones())


def test_can_generate_non_naive_time():
    assert minimal(times(timezones=timezones()),
                   lambda d: d.tzinfo).tzinfo == pytz.UTC


def test_can_generate_non_naive_datetime():
    assert minimal(datetimes(timezones=timezones()),
                   lambda d: d.tzinfo).tzinfo == pytz.UTC


@given(datetimes(timezones=timezones()))
def test_timezone_aware_datetimes_are_timezone_aware(dt):
    assert dt.tzinfo is not None


@given(sampled_from(['min_datetime', 'max_datetime']),
       datetimes(timezones=timezones()))
def test_datetime_bounds_must_be_naive(name, val):
    with pytest.raises(InvalidArgument):
        datetimes(**{name: val}).example()


def test_underflow_in_simplify():
    # we shouldn't trigger a pytz bug when we're simplifying
    minimal(datetimes(max_datetime=dt.datetime.min + dt.timedelta(days=3),
                      timezones=timezones()),
            lambda x: x.tzinfo != pytz.UTC)


def test_overflow_in_simplify():
    # we shouldn't trigger a pytz bug when we're simplifying
    minimal(datetimes(min_datetime=dt.datetime.max - dt.timedelta(days=3),
                      timezones=timezones()),
            lambda x: x.tzinfo != pytz.UTC)


def test_timezones_arg_to_datetimes_must_be_search_strategy():
    with pytest.raises(InvalidArgument):
        datetimes(timezones=pytz.all_timezones).example()
    with pytest.raises(InvalidArgument):
        tz = [pytz.timezone(t) for t in pytz.all_timezones]
        datetimes(timezones=tz).example()


@given(times(timezones=timezones()))
def test_timezone_aware_times_are_timezone_aware(dt):
    assert dt.tzinfo is not None


def test_can_generate_non_utc():
    minimal(times(timezones=timezones()),
            lambda d: assume(d.tzinfo) and d.tzinfo.zone != u'UTC')


@given(sampled_from(['min_time', 'max_time']), times(timezones=timezones()))
def test_time_bounds_must_be_naive(name, val):
    with pytest.raises(InvalidArgument):
        times(**{name: val}).example()
