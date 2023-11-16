# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import HealthCheck, assume, example, given, settings, strategies as st
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


def IntervalLists(min_size=0):
    return st.lists(
        st.tuples(st.integers(0, 200), st.integers(0, 20)),
        min_size=min_size,
    ).map(build_intervals)


Intervals = st.builds(IntervalSet, IntervalLists())


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


@example(intervals=IntervalSet(((1, 1),)), v=0)
@example(intervals=IntervalSet(()), v=0)
@given(Intervals, st.integers(0, 0x10FFFF))
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


@settings(suppress_health_check=[HealthCheck.filter_too_much])
@example(x=[(0, 1), (3, 3)], y=[(1, 3)])
@example(x=[(0, 1)], y=[(0, 0), (1, 1)])
@example(x=[(0, 1)], y=[(1, 1)])
@given(IntervalLists(min_size=1), IntervalLists(min_size=1))
def test_subtraction_of_intervals(x, y):
    xs = intervals_to_set(x)
    ys = intervals_to_set(y)
    assume(not xs.isdisjoint(ys))
    z = IntervalSet(x).difference(IntervalSet(y)).intervals
    assert z == tuple(sorted(z))
    for a, b in z:
        assert a <= b
    assert intervals_to_set(z) == intervals_to_set(x) - intervals_to_set(y)


@given(Intervals, Intervals)
def test_interval_intersection(x, y):
    print(f"{set(x)=} {set(y)=} {set(x)-(set(y)-set(x))=}")
    assert set(x & y) == set(x) & set(y)
    assert set(x.intersection(y)) == set(x).intersection(y)


def test_char_in_shrink_order():
    xs = IntervalSet([(0, 256)])
    assert xs[xs._idx_of_zero] == ord("0")
    assert xs[xs._idx_of_Z] == ord("Z")
    rewritten = [ord(xs.char_in_shrink_order(i)) for i in range(256)]
    assert rewritten != list(range(256))
    assert sorted(rewritten) == sorted(range(256))
