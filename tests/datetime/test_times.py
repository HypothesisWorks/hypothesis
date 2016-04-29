# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

import pytz

import hypothesis._settings as hs
from hypothesis import given, assume
from hypothesis.strategytests import strategy_test_suite
from hypothesis.extra.datetime import times
from hypothesis.internal.debug import minimal

TestStandardDescriptorFeatures1 = strategy_test_suite(times())


def test_can_find_midnight():
    minimal(
        times(),
        lambda x: (x.hour == 0 and x.minute == 0 and x.second == 0),
    )


def test_can_find_non_midnight():
    assert minimal(times(), lambda x: x.hour != 0).hour == 1


def test_can_find_off_the_minute():
    minimal(times(), lambda x: x.second == 0)


def test_can_find_on_the_minute():
    minimal(times(), lambda x: x.second != 0)


def test_simplifies_towards_midnight():
    d = minimal(times())
    assert d.hour == 0
    assert d.minute == 0
    assert d.second == 0
    assert d.microsecond == 0


def test_can_generate_naive_time():
    minimal(times(allow_naive=True), lambda d: not d.tzinfo)


def test_can_generate_non_naive_time():
    assert minimal(
        times(allow_naive=True), lambda d: d.tzinfo).tzinfo == pytz.UTC


def test_can_generate_non_utc():
    minimal(
        times(),
        lambda d: assume(d.tzinfo) and d.tzinfo.zone != u'UTC')


with hs.settings(max_examples=1000):
    @given(times(timezones=[]))
    def test_naive_times_are_naive(dt):
        assert not dt.tzinfo

    @given(times(allow_naive=False))
    def test_timezone_aware_times_are_timezone_aware(dt):
        assert dt.tzinfo


def test_restricts_to_allowed_set_of_timezones():
    timezones = list(map(pytz.timezone, list(pytz.all_timezones)[:3]))
    x = minimal(times(timezones=timezones))
    assert any(tz.zone == x.tzinfo.zone for tz in timezones)
