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
from flaky import flaky

import hypothesis._settings as hs
from hypothesis import find, given, assume, settings
from hypothesis.errors import InvalidArgument
from tests.common.debug import minimal
from tests.common.utils import checks_deprecated_behaviour
from hypothesis.strategytests import strategy_test_suite
from hypothesis.extra.datetime import datetimes
from hypothesis.internal.compat import hrange

TestStandardDescriptorFeatures1 = strategy_test_suite(datetimes())
TestStandardDescriptorFeatures2 = strategy_test_suite(
    datetimes(allow_naive=False))
TestStandardDescriptorFeatures3 = strategy_test_suite(
    datetimes(timezones=[]),
)


def test_can_find_after_the_year_2000():
    assert minimal(datetimes(), lambda x: x.year > 2000).year == 2001


def test_can_find_before_the_year_2000():
    assert minimal(datetimes(), lambda x: x.year < 2000).year == 1999


def test_can_find_each_month():
    for i in hrange(1, 12):
        minimal(datetimes(), lambda x: x.month == i)


def test_can_find_midnight():
    minimal(
        datetimes(),
        lambda x: (x.hour == 0 and x.minute == 0 and x.second == 0),
    )


def test_can_find_non_midnight():
    assert minimal(datetimes(), lambda x: x.hour != 0).hour == 1


def test_can_find_off_the_minute():
    minimal(datetimes(), lambda x: x.second == 0)


def test_can_find_on_the_minute():
    minimal(datetimes(), lambda x: x.second != 0)


def test_simplifies_towards_midnight():
    d = minimal(datetimes())
    assert d.hour == 0
    assert d.minute == 0
    assert d.second == 0
    assert d.microsecond == 0


def test_can_generate_naive_datetime():
    minimal(datetimes(allow_naive=True), lambda d: not d.tzinfo)


def test_can_generate_non_naive_datetime():
    assert minimal(
        datetimes(allow_naive=True), lambda d: d.tzinfo).tzinfo == pytz.UTC


def test_can_generate_non_utc():
    minimal(
        datetimes(),
        lambda d: assume(d.tzinfo) and d.tzinfo.zone != u'UTC')


with hs.settings(max_examples=1000):
    @given(datetimes(timezones=[]))
    def test_naive_datetimes_are_naive(d):
        assert not d.tzinfo

    @given(datetimes(allow_naive=False))
    def test_timezone_aware_datetimes_are_timezone_aware(d):
        assert d.tzinfo


def test_restricts_to_allowed_set_of_timezones():
    timezones = list(map(pytz.timezone, list(pytz.all_timezones)[:3]))
    x = minimal(datetimes(timezones=timezones))
    assert any(tz.zone == x.tzinfo.zone for tz in timezones)


@checks_deprecated_behaviour
def test_min_year_is_respected():
    assert minimal(datetimes(min_year=2003)).year == 2003


@checks_deprecated_behaviour
def test_max_year_is_respected():
    assert minimal(datetimes(max_year=1998)).year == 1998


def test_min_datetime_is_respected():
    d = dt.datetime(2003, 3, 4, 5, 6, 7, 8000)
    assert minimal(datetimes(min_datetime=d, timezones=[])) == d


def test_max_datetime_is_respected():
    d = dt.datetime(1998, 7, 6, 5, 4, 3, 2000)
    assert minimal(datetimes(max_datetime=d, timezones=[])) == \
        dt.datetime.min.replace(year=1998)


@checks_deprecated_behaviour
def test_validates_year_arguments_in_range():
    with pytest.raises(InvalidArgument):
        datetimes(min_year=-10 ** 6).example()
    with pytest.raises(InvalidArgument):
        datetimes(max_year=-10 ** 6).example()
    with pytest.raises(InvalidArgument):
        datetimes(min_year=10 ** 6).example()
    with pytest.raises(InvalidArgument):
        datetimes(max_year=10 ** 6).example()


def test_needs_permission_for_no_timezones():
    with pytest.raises(InvalidArgument):
        datetimes(allow_naive=False, timezones=[]).example()


@flaky(max_runs=3, min_passes=1)
def test_bordering_on_a_leap_year():
    x = find(
        datetimes(min_datetime=dt.date(2003, 1, 1),
                  max_datetime=dt.date(2005, 12, 31)),
        lambda x: x.month == 2 and x.day == 29,
        settings=settings(database=None, max_examples=10 ** 7, timeout=-1)
    )
    assert x.year == 2004


def test_can_draw_constrained_value_naive():
    start = dt.datetime.min.replace(year=2001)
    end = start + dt.timedelta(microseconds=100)
    drawn = datetimes(timezones=[],
                      min_datetime=start, max_datetime=end).example()
    assert start <= drawn <= end


def test_can_draw_constrained_value_aware():
    start = pytz.utc.localize(dt.datetime.min.replace(year=2001))
    end = start + dt.timedelta(microseconds=100)
    drawn = datetimes(min_datetime=start, max_datetime=end).example()
    assert start <= drawn <= end


def test_overflow_in_simplify():
    """This is a test that we don't trigger a pytz bug when we're simplifying
    around datetime.min where valid dates can produce an overflow error."""
    minimal(
        datetimes(max_datetime=dt.datetime.min.replace(month=2)),
        lambda x: x.tzinfo != pytz.UTC
    )


def test_cannot_mix_old_new_arguments():
    with pytest.raises(InvalidArgument):
        datetimes(min_year=2000, max_datetime=dt.date(2001, 1, 1)).example()


@pytest.mark.parametrize('arg', [2000, 2000.00, '2000-01-01'])
def test_wrong_argument_type(arg):
    with pytest.raises(InvalidArgument):
        datetimes(max_datetime=arg).example()


def test_cannot_draw_naive_from_aware_bounds():
    with pytest.raises(InvalidArgument):
        datetimes(allow_naive=True, min_datetime=pytz.utc.localize(
            dt.datetime.min.replace(year=2000))).example()


def test_can_draw_aware_from_aware_bounds():
    ex = datetimes(max_datetime=pytz.utc.localize(dt.datetime.max)).example()
    assert ex.tzinfo is not None


def test_can_draw_naive_from_naive_bounds():
    assert datetimes(timezones=[]).example().tzinfo is None


def test_can_draw_aware_from_naive_bounds():
    assert datetimes(allow_naive=False).example().tzinfo is not None


def test_cannot_mix_aware_naive_bounds():
    with pytest.raises(InvalidArgument):
        datetimes(min_datetime=pytz.utc.localize(dt.datetime.min),
                  max_datetime=dt.datetime.max - dt.timedelta(days=1)
                  ).example()


@given(x=datetimes(timezones=[]), y=datetimes(timezones=[]))
def test_naive_bounds(x, y):
    min_dt, max_dt = sorted([x, y])
    strat = datetimes(min_datetime=min_dt, max_datetime=max_dt, timezones=[])
    assert min_dt <= strat.example() <= max_dt


@given(x=datetimes(allow_naive=False), y=datetimes(allow_naive=False))
def test_aware_bounds(x, y):
    min_dt, max_dt = sorted([x, y])
    strat = datetimes(min_datetime=min_dt, max_datetime=max_dt)
    assert min_dt <= strat.example() <= max_dt


def test_validate_min_max_datetime_arg_types():
    with pytest.raises(InvalidArgument):
        datetimes(min_datetime=2000).example()
    with pytest.raises(InvalidArgument):
        datetimes(max_datetime=2000).example()


def test_handles_identical_bounds():
    # Equivalent to just(day).example()
    day = dt.datetime.min.replace(2001, 1, 1)
    assert datetimes(min_datetime=day, max_datetime=day,
                     timezones=[]).example() == day
    utc_day = pytz.utc.normalize(pytz.utc.localize(day))
    to_tz = pytz.timezone('Australia/Sydney')
    assert datetimes(min_datetime=utc_day, max_datetime=utc_day,
                     timezones=[to_tz]).example() == utc_day.astimezone(to_tz)


def test_aware_bounds_require_timezones():
    start = pytz.utc.localize(dt.datetime.min.replace(2003, 4, 5))
    end = start + dt.timedelta(days=20, hours=6)
    with pytest.raises(InvalidArgument):
        datetimes(min_datetime=start, max_datetime=end, timezones=[]).example()


def test_disallow_always_underflow_overflow():
    utc_min = pytz.utc.localize(dt.datetime.min)
    with pytest.raises(InvalidArgument):
        datetimes(min_datetime=utc_min, max_datetime=utc_min,
                  timezones=['Pacific/Galapagos']).example()
    utc_max = pytz.utc.localize(dt.datetime.max)
    with pytest.raises(InvalidArgument):
        datetimes(min_datetime=utc_max, max_datetime=utc_max,
                  timezones=['Australia/Sydney']).example()


def test_handles_might_overflow():
    utc_min = pytz.utc.localize(dt.datetime.min)
    minimal(datetimes(min_datetime=utc_min, max_datetime=utc_min))


def test_handles_might_underflow():
    utc_max = pytz.utc.localize(dt.datetime.max)
    minimal(datetimes(min_datetime=utc_max, max_datetime=utc_max))
