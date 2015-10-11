# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

from random import Random
from datetime import MAXYEAR

import pytest

import hypothesis.settings as hs
from hypothesis.strategytests import strategy_test_suite
from hypothesis.extra.datetime import dates
from hypothesis.internal.debug import minimal
from hypothesis.internal.compat import hrange
from hypothesis.searchstrategy.strategies import BadData

hs.Settings.default.max_examples = 1000


TestStandardDescriptorFeatures1 = strategy_test_suite(dates())


def test_can_find_after_the_year_2000():
    assert minimal(dates(), lambda x: x.year > 2000).year == 2001


def test_can_find_before_the_year_2000():
    assert minimal(dates(), lambda x: x.year < 2000).year == 1999


def test_can_find_each_month():
    for i in hrange(1, 12):
        minimal(dates(), lambda x: x.month == i)


def test_min_year_is_respected():
    assert minimal(dates(min_year=2003)).year == 2003


def test_max_year_is_respected():
    assert minimal(dates(max_year=1998)).year == 1998


def test_year_bounds_are_respected_in_deserialization():
    s = dates()
    r = Random(1)
    template = s.draw_template(r, s.draw_parameter(r))
    year = s.reify(template).year
    basic = s.to_basic(template)
    above = dates(min_year=year + 1)
    below = dates(max_year=year - 1)
    with pytest.raises(BadData):
        above.from_basic(basic)
    with pytest.raises(BadData):
        below.from_basic(basic)


def test_can_draw_times_in_the_final_year():
    last_year = dates(min_year=MAXYEAR)
    r = Random(1)
    for _ in hrange(1000):
        last_year.reify(last_year.draw_and_produce(r))
