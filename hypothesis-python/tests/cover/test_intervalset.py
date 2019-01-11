# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import pytest

import hypothesis.strategies as st
from hypothesis import assume, example, given
from hypothesis.internal.charmap import _subtract_intervals
from hypothesis.internal.intervalsets import IntervalSet


def build_intervals(ls):
    ls.sort()
    result = []
    for u, l in ls:
        v = u + l
        if result:
            a, b = result[-1]
            if u <= b + 1:
                result[-1] = (a, v)
                continue
        result.append((u, v))
    return result


IntervalLists = st.builds(
    build_intervals, st.lists(st.tuples(st.integers(0, 200), st.integers(0, 20)))
)

Intervals = st.builds(IntervalSet, IntervalLists)


@given(Intervals)
def test_intervals_are_equivalent_to_their_lists(intervals):
    ls = list(intervals)
    assert len(ls) == len(intervals)
    for i in range(len(ls)):
        assert ls[i] == intervals[i]
    for i in range(1, len(ls) - 1):
        assert ls[-i] == intervals[-i]


@given(Intervals)
def test_intervals_match_indexes(intervals):
    ls = list(intervals)
    for v in ls:
        assert ls.index(v) == intervals.index(v)


@example(intervals=IntervalSet(()), v=0)
@given(Intervals, st.integers())
def test_error_for_index_of_not_present_value(intervals, v):
    assume(v not in intervals)
    with pytest.raises(ValueError):
        intervals.index(v)


def test_validates_index():
    with pytest.raises(IndexError):
        IntervalSet([])[1]

    with pytest.raises(IndexError):
        IntervalSet([[1, 10]])[11]

    with pytest.raises(IndexError):
        IntervalSet([[1, 10]])[-11]


def test_index_above_is_index_if_present():
    assert IntervalSet([[1, 10]]).index_above(1) == 0
    assert IntervalSet([[1, 10]]).index_above(2) == 1


def test_index_above_is_length_if_higher():
    assert IntervalSet([[1, 10]]).index_above(100) == 10


def intervals_to_set(ints):
    return set(IntervalSet(ints))


@example(x=[(0, 1), (3, 3)], y=[(1, 3)])
@example(x=[(0, 1)], y=[(0, 0), (1, 1)])
@example(x=[(0, 1)], y=[(1, 1)])
@given(IntervalLists, IntervalLists)
def test_subtraction_of_intervals(x, y):
    xs = intervals_to_set(x)
    ys = intervals_to_set(x)
    assume(not xs.isdisjoint(ys))
    z = _subtract_intervals(x, y)
    assert z == tuple(sorted(z))
    for a, b in z:
        assert a <= b
    assert intervals_to_set(z) == intervals_to_set(x) - intervals_to_set(y)
