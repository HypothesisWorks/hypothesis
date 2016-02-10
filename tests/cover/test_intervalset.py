# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import hypothesis.strategies as st
from hypothesis import given
from hypothesis.internal.intervalsets import IntervalSet


def build_intervals(ls):
    ls.sort()
    result = []
    for u, l in ls:
        v = u + l
        if result:
            a, b = result[-1]
            if u <= b:
                result[-1] = (a, v)
                continue
        result.append((u, v))
    return IntervalSet(result)


Intervals = st.builds(
    build_intervals,
    st.lists(st.tuples(st.integers(), st.integers(0, 20)))
)


@given(Intervals)
def test_intervals_are_equivalent_to_their_lists(intervals):
    ls = list(intervals)
    assert len(ls) == len(intervals)
    for i in range(len(ls)):
        assert ls[i] == intervals[i]
    for i in range(1, len(ls) - 1):
        assert ls[-i] == intervals[-i]
