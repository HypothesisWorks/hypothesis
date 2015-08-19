# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import random

import pytest
from hypothesis.errors import InvalidArgument
from hypothesis.internal.chooser import chooser


def test_cannot_choose_empty():
    with pytest.raises(InvalidArgument):
        chooser([])


def test_cannot_choose_negative_weights():
    with pytest.raises(InvalidArgument):
        chooser((1, -1, 1))


def test_can_choose_zero_weights():
    assert chooser([1, 0, 0, 0]).choose(random) == 0


def test_cannot_choose_all_zero_weights():
    with pytest.raises(InvalidArgument):
        chooser([0])


def test_can_choose_one():
    chooser([1]).choose(random) == 0
