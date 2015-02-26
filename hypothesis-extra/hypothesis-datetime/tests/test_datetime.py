# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from datetime import datetime

import hypothesis.settings as hs
from hypothesis import Verifier, given, assume
from hypothesis.descriptors import one_of
from hypothesis.extra.datetime import naive_datetime, \
    timezone_aware_datetime
from hypothesis.descriptortests import descriptor_test_suite
from hypothesis.internal.compat import hrange
from hypothesis.searchstrategy.table import StrategyTable

hs.default.max_examples = 1000


TestStandardDescriptorFeatures1 = descriptor_test_suite(datetime)
TestStandardDescriptorFeatures2 = descriptor_test_suite(
    timezone_aware_datetime)
TestStandardDescriptorFeatures3 = descriptor_test_suite(naive_datetime)
TestStandardDescriptorFeatures4 = descriptor_test_suite(one_of((
    naive_datetime,
    timezone_aware_datetime,
)))


falsify = Verifier().falsify


def test_can_find_after_the_year_2000():
    falsify(lambda x: x.year > 2000, datetime)


def test_can_find_before_the_year_2000():
    falsify(lambda x: x.year < 2000, datetime)


def test_can_find_each_month():
    for i in hrange(1, 12):
        falsify(lambda x: x.month != i, datetime)


def test_can_find_midnight():
    falsify(
        lambda x: not (x.hour == 0 and x.minute == 0 and x.second == 0),
        datetime
    )


def test_can_find_non_midnight():
    falsify(lambda x: x.hour == 0, datetime)


def test_can_find_off_the_minute():
    falsify(lambda x: x.second == 0, datetime)


def test_can_find_on_the_minute():
    falsify(lambda x: x.second != 0, datetime)


def test_can_find_february_29():
    falsify(lambda d: assume(d.month == 2) and (d.day != 29), datetime)


def test_can_find_christmas():
    falsify(lambda d: assume(d.month == 12) and d.day == 25, datetime)


def test_simplifies_towards_midnight():
    d = falsify(lambda x: False, datetime)[0]
    assert d.hour == 0
    assert d.minute == 0
    assert d.second == 0
    assert d.microsecond == 0


def test_simplifies_towards_2000():
    d = falsify(lambda x: x.year <= 2000, datetime)[0]
    assert d.year == 2001
    d = falsify(lambda x: x.year >= 2000, datetime)[0]
    assert d.year == 1999


def test_can_generate_naive_datetime():
    falsify(lambda d: d.tzinfo, datetime)


def test_can_generate_non_naive_datetime():
    falsify(lambda d: not d.tzinfo, datetime)


def test_can_generate_non_utc():
    falsify(lambda d: assume(d.tzinfo) and d.tzinfo.zone == 'UTC', datetime)


def test_can_generate_utc():
    falsify(lambda d: assume(d.tzinfo) and d.tzinfo.zone != 'UTC', datetime)


def test_can_simplify_leap_years():
    s = StrategyTable().strategy(datetime)
    d = datetime(
        year=2012, month=2, day=29
    )
    t = list(
        s.simplify_such_that(
            d, lambda x: (x.month == 2) and (x.day == 29) and (x.year > 2000))
    )[-1]
    assert t.year == 2004


@given(naive_datetime)
def test_naive_datetimes_are_naive(dt):
    assert not dt.tzinfo


@given(timezone_aware_datetime)
def test_timezone_aware_datetimes_are_timezone_aware(dt):
    assert dt.tzinfo
