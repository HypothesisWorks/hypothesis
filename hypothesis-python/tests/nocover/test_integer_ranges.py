# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import pytest

from hypothesis.internal.conjecture.utils import integer_range
from hypothesis.searchstrategy.strategies import SearchStrategy
from tests.common.debug import minimal


class interval(SearchStrategy):
    def __init__(self, lower, upper, center=None):
        self.lower = lower
        self.upper = upper
        self.center = center

    def do_draw(self, data):
        return integer_range(data, self.lower, self.upper, center=self.center)


@pytest.mark.parametrize("inter", [(0, 5, 10), (-10, 10, 10), (0, 1, 1), (1, 1, 2)])
def test_intervals_shrink_to_center(inter):
    lower, center, upper = inter
    s = interval(lower, upper, center)
    assert minimal(s, lambda x: True) == center
    if lower < center:
        assert minimal(s, lambda x: x < center) == center - 1
    if center < upper:
        assert minimal(s, lambda x: x > center) == center + 1
