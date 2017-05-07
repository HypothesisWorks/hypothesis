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

from hypothesis import given
from hypothesis.errors import InvalidArgument
from tests.common.debug import minimal
from tests.common.utils import checks_deprecated_behaviour
from hypothesis.strategytests import strategy_test_suite
from hypothesis.extra.datetime import dates
from hypothesis.internal.compat import hrange

TestStandardDescriptorFeatures1 = strategy_test_suite(dates())


def test_can_find_after_the_year_2000():
    assert minimal(dates(), lambda x: x.year > 2000).year == 2001


def test_can_find_before_the_year_2000():
    assert minimal(dates(), lambda x: x.year < 2000).year == 1999


def test_can_find_each_month():
    for i in hrange(1, 12):
        minimal(dates(), lambda x: x.month == i)


@checks_deprecated_behaviour
def test_min_year_is_respected():
    assert minimal(dates(min_year=2003)).year == 2003


@checks_deprecated_behaviour
def test_max_year_is_respected():
    assert minimal(dates(max_year=1998)).year == 1998


def test_min_date_is_respected():
    d = dt.date(2003, 7, 12)
    assert minimal(dates(min_date=d)) == d


def test_max_date_is_respected():
    d = dt.date(1998, 5, 17)
    assert minimal(dates(max_date=d)) == dt.date.min.replace(year=d.year)


def test_can_give_datetime_bounds():
    dates(min_date=dt.datetime.min, max_date=dt.datetime.max).example()


@given(x=dates(), y=dates())
def test_bounds(x, y):
    min_date, max_date = sorted([x, y])
    strat = dates(min_date=min_date, max_date=max_date)
    assert min_date <= strat.example() <= max_date


def test_cannot_mix_old_new_arguments():
    with pytest.raises(InvalidArgument):
        dates(min_year=2000, max_date=dt.date(2001, 1, 1)).example()


def test_validate_min_max_date_arg_types():
    with pytest.raises(InvalidArgument):
        dates(min_date=2000).example()
    with pytest.raises(InvalidArgument):
        dates(max_date=2000).example()


def test_handles_identical_bounds():
    # Equivalent to just(day).example()
    day = dt.date(2001, 1, 1)
    assert dates(min_date=day, max_date=day).example() == day
