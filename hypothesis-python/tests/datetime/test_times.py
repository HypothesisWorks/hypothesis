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

import pytz

from hypothesis import assume, given
from hypothesis.extra.datetime import times
from tests.common.debug import find_any, minimal
from tests.common.utils import checks_deprecated_behaviour


@checks_deprecated_behaviour
def test_can_find_midnight():
    find_any(times(), lambda x: x.hour == x.minute == x.second == 0)


@checks_deprecated_behaviour
def test_can_find_non_midnight():
    assert minimal(times(), lambda x: x.hour != 0).hour == 1


@checks_deprecated_behaviour
def test_can_find_off_the_minute():
    find_any(times(), lambda x: x.second != 0)


@checks_deprecated_behaviour
def test_can_find_on_the_minute():
    find_any(times(), lambda x: x.second == 0)


@checks_deprecated_behaviour
def test_simplifies_towards_midnight():
    d = minimal(times())
    assert d.hour == 0
    assert d.minute == 0
    assert d.second == 0
    assert d.microsecond == 0


@checks_deprecated_behaviour
def test_can_generate_naive_time():
    find_any(times(allow_naive=True), lambda d: d.tzinfo is not None)


@checks_deprecated_behaviour
def test_can_generate_non_naive_time():
    assert minimal(times(allow_naive=True), lambda d: d.tzinfo).tzinfo == pytz.UTC


@checks_deprecated_behaviour
def test_can_generate_non_utc():
    times().filter(lambda d: assume(d.tzinfo) and d.tzinfo.zone != u"UTC").example()


@checks_deprecated_behaviour
@given(times(timezones=[]))
def test_naive_times_are_naive(dt):
    assert not dt.tzinfo


@checks_deprecated_behaviour
@given(times(allow_naive=False))
def test_timezone_aware_times_are_timezone_aware(dt):
    assert dt.tzinfo


@checks_deprecated_behaviour
def test_restricts_to_allowed_set_of_timezones():
    timezones = list(map(pytz.timezone, list(pytz.all_timezones)[:3]))
    x = minimal(times(timezones=timezones))
    assert any(tz.zone == x.tzinfo.zone for tz in timezones)
