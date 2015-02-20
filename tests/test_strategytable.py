# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import hypothesis.descriptors as descriptors
import hypothesis.strategytable as st
import hypothesis.searchstrategy as strat


def test_strategies_can_be_used_in_descriptors():
    intxfloat = st.StrategyTable.default().strategy((
        int, strat.ExponentialFloatStrategy()
    ))
    assert intxfloat.descriptor == (int, float)


def test_has_strategy_for_frozensets():
    assert (
        st.StrategyTable.default().strategy(frozenset([int])).descriptor ==
        frozenset([int]))


def test_has_strategy_for_samples():
    table = st.StrategyTable.default()
    sampling = descriptors.sampled_from([1, 2, 3])
    assert table.has_specification_for(sampling)
    assert table.has_specification_for([sampling])
    assert table.has_specification_for(set([sampling]))
