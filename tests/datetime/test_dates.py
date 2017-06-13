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

from tests.common.debug import minimal
from tests.common.utils import checks_deprecated_behaviour
from hypothesis.extra.datetime import dates
from hypothesis.internal.compat import hrange


@checks_deprecated_behaviour
def test_can_find_after_the_year_2000():
    assert minimal(dates(), lambda x: x.year > 2000).year == 2001


@checks_deprecated_behaviour
def test_can_find_before_the_year_2000():
    assert minimal(dates(), lambda x: x.year < 2000).year == 1999


@checks_deprecated_behaviour
def test_can_find_each_month():
    for month in hrange(1, 13):
        dates().filter(lambda x: x.month == month).example()


@checks_deprecated_behaviour
def test_min_year_is_respected():
    assert minimal(dates(min_year=2003)).year == 2003


@checks_deprecated_behaviour
def test_max_year_is_respected():
    assert minimal(dates(max_year=1998)).year == 1998
