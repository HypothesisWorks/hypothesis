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

import hypothesis.strategies as st
from hypothesis import find, given, settings
from hypothesis.internal.conjecture.data import TestData
from hypothesis.internal.conjecture.utils import integer_range
from hypothesis.searchstrategy.strategies import SearchStrategy


class interval(SearchStrategy):

    def __init__(self, lower, upper, center=None, distribution=None):
        self.lower = lower
        self.upper = upper
        self.center = center
        self.distribution = distribution

    def do_draw(self, data):
        return integer_range(
            data, self.lower, self.upper, center=self.center,
            distribution=self.distribution,
        )


@given(
    st.tuples(st.integers(), st.integers(), st.integers()).map(sorted),
    st.random_module(),
)
@settings(timeout=10, max_shrinks=0)
def test_intervals_shrink_to_center(inter, rnd):
    lower, center, upper = inter
    s = interval(lower, upper, center)
    with settings(database=None, max_shrinks=2000):
        assert find(s, lambda x: True) == center
        if lower < center:
            assert find(s, lambda x: x < center) == center - 1
        if center < upper:
            assert find(s, lambda x: x > center) == center + 1


@given(
    st.tuples(
        st.integers(), st.integers(), st.integers(), st.integers()
    ).map(sorted),
    st.randoms(),
)
@settings(timeout=10, max_shrinks=0)
def test_distribution_is_correctly_translated(inter, rnd):
    assert inter == sorted(inter)
    lower, c1, c2, upper = inter
    d = TestData(
        draw_bytes=lambda data, n, distribution: distribution(rnd, n),
        max_length=10 ** 6
    )
    assert d.draw(interval(lower, upper, c1, lambda r: c2)) == c2
    assert d.draw(interval(lower, upper, c2, lambda r: c1)) == c1
