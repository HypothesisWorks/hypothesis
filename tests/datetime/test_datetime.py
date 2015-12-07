# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

from random import Random
from datetime import MAXYEAR, MINYEAR, datetime

import pytz
import pytest

import hypothesis.settings as hs
from hypothesis import given, assume, Settings
from hypothesis.errors import InvalidArgument, UnsatisfiedAssumption
from hypothesis.strategytests import strategy_test_suite
from hypothesis.extra.datetime import datetimes, any_datetime, \
    naive_datetime, timezone_aware_datetime
from hypothesis.internal.debug import minimal, some_template
from hypothesis.internal.compat import hrange
from hypothesis.searchstrategy.strategies import BadData

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


with hs.Settings(max_examples=1000):
    @given(datetimes(timezones=[]))
    def test_naive_datetimes_are_naive(dt):
        assert not dt.tzinfo

    @given(datetimes(allow_naive=False))
    def test_timezone_aware_datetimes_are_timezone_aware(dt):
        assert dt.tzinfo


def test_restricts_to_allowed_set_of_timezones():
    timezones = list(map(pytz.timezone, list(pytz.all_timezones)[:3]))
    x = minimal(datetimes(timezones=timezones))
    assert any(tz.zone == x.tzinfo.zone for tz in timezones)


def test_legacy_api():
    with hs.Settings(strict=False):
        x = minimal(datetime)
        assert x.tzinfo == pytz.UTC
        assert x.year == 2000

        assert minimal(naive_datetime).tzinfo is None
        assert minimal(timezone_aware_datetime) == x
        assert minimal(any_datetime) == x


def test_min_year_is_respected():
    assert minimal(datetimes(min_year=2003)).year == 2003


def test_max_year_is_respected():
    assert minimal(datetimes(max_year=1998)).year == 1998


def test_year_bounds_are_respected_in_deserialization():
    s = datetimes()
    r = Random(1)
    template = s.draw_template(r, s.draw_parameter(r))
    year = s.reify(template).year
    basic = s.to_basic(template)
    above = datetimes(min_year=year + 1)
    below = datetimes(max_year=year - 1)
    with pytest.raises(UnsatisfiedAssumption):
        above.reify(above.from_basic(basic))
    with pytest.raises(UnsatisfiedAssumption):
        below.reify(below.from_basic(basic))


def test_timezones_are_checked_in_deserialization():
    s = datetimes()
    r = Random(1)
    basic = s.to_basic(s.draw_template(r, s.draw_parameter(r)))
    with pytest.raises(UnsatisfiedAssumption):
        dts = datetimes(timezones=[])
        dts.reify(dts.from_basic(basic))


def test_can_draw_times_in_the_final_year():
    last_year = datetimes(min_year=MAXYEAR)
    r = Random(1)
    c = 0
    for _ in hrange(1000):
        try:
            last_year.reify(last_year.draw_and_produce(r))
            c += 1
        except UnsatisfiedAssumption:
            pass
    assert c >= 100


def test_validates_timezone_name_from_db():
    s = datetimes(allow_naive=False)
    template = some_template(s)
    basic = s.to_basic(template)
    basic[-1] = u"Cabbage"
    with pytest.raises(BadData):
        s.from_basic(basic)


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


def test_bordering_on_a_leap_year():
    x = minimal(
        datetimes(min_year=2002, max_year=2005),
        lambda x: x.month == 2 and x.day == 29,
        settings=Settings(database=None, max_examples=10 ** 7)
    )
    assert x.year == 2004


def test_overflow_in_simplify():
    """This is a test that we don't trigger a pytz bug when we're simplifying
    around MINYEAR where valid dates can produce an overflow error."""
    minimal(
        datetimes(max_year=MINYEAR),
        lambda x: x.tzinfo != pytz.UTC
    )
