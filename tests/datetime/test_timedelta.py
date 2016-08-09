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

import pytest

from hypothesis.errors import InvalidArgument
from hypothesis.extra.datetime import timedeltas
from hypothesis.internal.debug import minimal


def test_can_find_positive_delta():
    assert minimal(timedeltas(), lambda x: x.days > 0).days == 1


def test_can_find_negative_delta():
    assert minimal(timedeltas(), lambda x: x.days < 0).days == -1


def test_can_find_zero_delta():
    minimal(
        timedeltas(),
        lambda x: (x.days == 0 and x.seconds == 0 and x.microseconds == 0)
    )


def test_can_find_off_the_second():
    minimal(timedeltas(), lambda x: x.seconds == 0)


def test_can_find_on_the_second():
    minimal(timedeltas(), lambda x: x.seconds != 0)


def test_simplifies_towards_zero_delta():
    d = minimal(timedeltas())
    assert d.days == 0
    assert d.seconds == 0
    assert d.microseconds == 0


def test_min_days_is_respected():
    assert minimal(timedeltas(min_days=10)).days == 10


def test_max_days_is_respected():
    assert minimal(timedeltas(max_days=-10)).days == -10


def test_validates_days_arguments_in_range():
    with pytest.raises(InvalidArgument):
        timedeltas(min_days=-10 ** 10).example()
    with pytest.raises(InvalidArgument):
        timedeltas(max_days=-10 ** 10).example()
    with pytest.raises(InvalidArgument):
        timedeltas(min_days=10 ** 10).example()
    with pytest.raises(InvalidArgument):
        timedeltas(max_days=10 ** 10).example()
