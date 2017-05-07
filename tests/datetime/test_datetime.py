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

from datetime import MINYEAR

import pytz
import pytest
from flaky import flaky

import hypothesis._settings as hs
from hypothesis import find, given, assume, settings
from hypothesis.errors import InvalidArgument
from tests.common.debug import minimal
from tests.common.utils import checks_deprecated_behaviour
from hypothesis.extra.datetime import datetimes
from hypothesis.internal.compat import hrange


@checks_deprecated_behaviour
def test_can_find_after_the_year_2000():
    assert minimal(datetimes(), lambda x: x.year > 2000).year == 2001


@checks_deprecated_behaviour
def test_can_find_before_the_year_2000():
    assert minimal(datetimes(), lambda x: x.year < 2000).year == 1999


@checks_deprecated_behaviour
def test_can_find_each_month():
    for i in hrange(1, 12):
        minimal(datetimes(), lambda x: x.month == i)


@checks_deprecated_behaviour
def test_can_find_midnight():
    minimal(
        datetimes(),
        lambda x: (x.hour == 0 and x.minute == 0 and x.second == 0),
    )


@checks_deprecated_behaviour
def test_can_find_non_midnight():
    assert minimal(datetimes(), lambda x: x.hour != 0).hour == 1


@checks_deprecated_behaviour
def test_can_find_off_the_minute():
    minimal(datetimes(), lambda x: x.second == 0)


@checks_deprecated_behaviour
def test_can_find_on_the_minute():
    minimal(datetimes(), lambda x: x.second != 0)


@checks_deprecated_behaviour
def test_simplifies_towards_midnight():
    d = minimal(datetimes())
    assert d.hour == 0
    assert d.minute == 0
    assert d.second == 0
    assert d.microsecond == 0


@checks_deprecated_behaviour
def test_can_generate_naive_datetime():
    minimal(datetimes(allow_naive=True), lambda d: not d.tzinfo)


@checks_deprecated_behaviour
def test_can_generate_non_naive_datetime():
    assert minimal(
        datetimes(allow_naive=True), lambda d: d.tzinfo).tzinfo == pytz.UTC


@checks_deprecated_behaviour
def test_can_generate_non_utc():
    minimal(
        datetimes(),
        lambda d: assume(d.tzinfo) and d.tzinfo.zone != u'UTC')


with hs.settings(strict=False):
    @given(datetimes(timezones=[]))
    def test_naive_datetimes_are_naive(dt):
        assert not dt.tzinfo

    @given(datetimes(allow_naive=False))
    def test_timezone_aware_datetimes_are_timezone_aware(dt):
        assert dt.tzinfo


@checks_deprecated_behaviour
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


@checks_deprecated_behaviour
def test_needs_permission_for_no_timezones():
    with pytest.raises(InvalidArgument):
        datetimes(allow_naive=False, timezones=[]).example()


@checks_deprecated_behaviour
@flaky(max_runs=3, min_passes=1)
def test_bordering_on_a_leap_year():
    x = find(
        datetimes(min_year=2002, max_year=2005),
        lambda x: x.month == 2 and x.day == 29,
        settings=settings(database=None, max_examples=10 ** 7, timeout=-1)
    )
    assert x.year == 2004


@checks_deprecated_behaviour
def test_overflow_in_simplify():
    """This is a test that we don't trigger a pytz bug when we're simplifying
    around MINYEAR where valid dates can produce an overflow error."""
    minimal(
        datetimes(max_year=MINYEAR),
        lambda x: x.tzinfo != pytz.UTC
    )
