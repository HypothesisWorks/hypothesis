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

import pytest
from flaky import flaky

from hypothesis import find, given, settings
from tests.common.debug import minimal
from hypothesis.strategies import none, dates, times, binary, datetimes, \
    timedeltas
from hypothesis.strategytests import strategy_test_suite
from hypothesis.internal.compat import hrange
from hypothesis.searchstrategy.datetime import DatetimeStrategy
from hypothesis.internal.conjecture.data import Status, StopTest, \
    ConjectureData

TestStandardDescriptorFeatures_timedeltas1 = strategy_test_suite(timedeltas())


def test_can_find_positive_delta():
    assert minimal(timedeltas(), lambda x: x.days > 0) == dt.timedelta(1)


def test_can_find_negative_delta():
    assert minimal(timedeltas(max_delta=dt.timedelta(10**6)),
                   lambda x: x.days < 0) == dt.timedelta(-1)


def test_can_find_on_the_second():
    timedeltas().filter(lambda x: x.seconds == 0).example()


def test_can_find_off_the_second():
    timedeltas().filter(lambda x: x.seconds != 0).example()


def test_simplifies_towards_zero_delta():
    d = minimal(timedeltas())
    assert d.days == d.seconds == d.microseconds == 0


def test_min_value_is_respected():
    assert minimal(timedeltas(min_delta=dt.timedelta(days=10))).days == 10


def test_max_value_is_respected():
    assert minimal(timedeltas(max_delta=dt.timedelta(days=-10))).days == -10


@given(timedeltas())
def test_single_timedelta(val):
    assert timedeltas(val, val).example() is val


TestStandardDescriptorFeatures_datetimes1 = strategy_test_suite(datetimes())


def test_simplifies_towards_millenium():
    d = minimal(datetimes())
    assert d.year == 2000
    assert d.month == d.day == 1
    assert d.hour == d.minute == d.second == d.microsecond == 0


@given(datetimes())
def test_default_datetimes_are_naive(dt):
    assert dt.tzinfo is None


@flaky(max_runs=3, min_passes=1)
def test_bordering_on_a_leap_year():
    with settings(database=None, max_examples=10 ** 7, timeout=-1):
        x = minimal(datetimes(dt.datetime.min.replace(year=2003),
                              dt.datetime.max.replace(year=2005)),
                    lambda x: x.month == 2 and x.day == 29,
                    timeout_after=60)
    assert x.year == 2004


def test_DatetimeStrategy_draw_may_fail():
    def is_failure_inducing(b):
        try:
            return strat._attempt_one_draw(
                ConjectureData.for_buffer(b)) is None
        except StopTest:
            return False

    strat = DatetimeStrategy(dt.datetime.min, dt.datetime.max, none())
    failure_inducing = find(binary(), is_failure_inducing)
    data = ConjectureData.for_buffer(failure_inducing * 100)
    with pytest.raises(StopTest):
        data.draw(strat)
    assert data.status == Status.INVALID


TestStandardDescriptorFeatures_dates1 = strategy_test_suite(dates())


def test_can_find_after_the_year_2000():
    assert minimal(dates(), lambda x: x.year > 2000).year == 2001


def test_can_find_before_the_year_2000():
    assert minimal(dates(), lambda x: x.year < 2000).year == 1999


def test_can_find_each_month():
    for month in hrange(1, 13):
        dates().filter(lambda x: x.month == month).example()


def test_min_year_is_respected():
    assert minimal(dates(min_date=dt.date.min.replace(2003))).year == 2003


def test_max_year_is_respected():
    assert minimal(dates(max_date=dt.date.min.replace(1998))).year == 1998


@given(dates())
def test_single_date(val):
    assert dates(val, val).example() is val


TestStandardDescriptorFeatures_times1 = strategy_test_suite(times())


def test_can_find_midnight():
    times().filter(lambda x: x.hour == x.minute == x.second == 0).example()


def test_can_find_non_midnight():
    assert minimal(times(), lambda x: x.hour != 0).hour == 1


def test_can_find_on_the_minute():
    times().filter(lambda x: x.second == 0).example()


def test_can_find_off_the_minute():
    times().filter(lambda x: x.second != 0).example()


def test_simplifies_towards_midnight():
    d = minimal(times())
    assert d.hour == d.minute == d.second == d.microsecond == 0


def test_can_generate_naive_time():
    times().filter(lambda d: not d.tzinfo).example()


@given(times())
def test_naive_times_are_naive(dt):
    assert dt.tzinfo is None
