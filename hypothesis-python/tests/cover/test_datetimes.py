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

from hypothesis import given, settings
from hypothesis.internal.compat import PYPY
from hypothesis.strategies import dates, datetimes, timedeltas, times
from tests.common.debug import find_any, minimal


def test_can_find_positive_delta():
    assert minimal(timedeltas(), lambda x: x.days > 0) == dt.timedelta(1)


def test_can_find_negative_delta():
    assert minimal(
        timedeltas(max_value=dt.timedelta(10 ** 6)), lambda x: x.days < 0
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


@given(timedeltas())
def test_single_timedelta(val):
    assert find_any(timedeltas(val, val)) is val


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
        timeout_after=60,
    )
    assert x.year == 2004


def test_can_find_after_the_year_2000():
    assert minimal(dates(), lambda x: x.year > 2000).year == 2001


def test_can_find_before_the_year_2000():
    assert minimal(dates(), lambda x: x.year < 2000).year == 1999


@pytest.mark.parametrize("month", range(1, 13))
def test_can_find_each_month(month):
    find_any(dates(), lambda x: x.month == month, settings(max_examples=10 ** 6))


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


# pypy3.6 seems to canonicalise fold to 0 for non-ambiguous times?
@pytest.mark.skipif(PYPY, reason="see comment")
def test_can_generate_datetime_with_fold_1():
    find_any(datetimes(), lambda d: d.fold)


@pytest.mark.skipif(PYPY, reason="see comment")
def test_can_generate_time_with_fold_1():
    find_any(times(), lambda d: d.fold)
