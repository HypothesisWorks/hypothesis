# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis.searchstrategy import strategy
from hypothesis.searchstrategy.numbers import ExponentialFloatStrategy


def test_strategies_can_be_used_in_descriptors():
    intxfloat = strategy((
        int, ExponentialFloatStrategy()
    ))
    assert intxfloat.descriptor == (int, float)


def test_has_strategy_for_frozensets():
    assert (
        strategy(frozenset([int])).descriptor ==
        frozenset([int]))
