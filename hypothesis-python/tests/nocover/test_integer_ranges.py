# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import pytest

from hypothesis import given
from hypothesis.internal.conjecture.utils import integer_range
from hypothesis.strategies import integers
from hypothesis.strategies._internal.strategies import SearchStrategy
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


def test_bounded_integers_distribution_of_bit_width_issue_1387_regression():
    values = []

    @given(integers(0, 1e100))
    def test(x):
        values.append(x)

    test()

    # We draw from a shaped distribution up to 128bit ~7/8 of the time, and
    # uniformly the rest.  So we should get some very large but not too many.
    huge = sum(x > 1e97 for x in values)
    assert huge != 0
    assert huge <= 0.3 * len(values)  # expected ~1/8
