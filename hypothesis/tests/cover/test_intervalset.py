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

from hypothesis import assume, example, given, settings, strategies as st
from hypothesis.internal.conjecture.provider_conformance import (
    interval_lists,
    intervals,
)
from hypothesis.internal.intervalsets import IntervalSet

# various tests in this file impose a max_codepoint restriction on intervals,
# for performance. There may be possibilities for performance improvements in
# IntervalSet itself as well.


@given(intervals(max_codepoint=200))
@settings(deadline=None)
def test_intervals_are_equivalent_to_their_lists(intervals):
    ls = list(intervals)
    assert len(ls) == len(intervals)
    for i in range(len(ls)):
        assert ls[i] == intervals[i]
    for i in range(1, len(ls) - 1):
        assert ls[-i] == intervals[-i]


@given(intervals(max_codepoint=200))
def test_intervals_match_indexes(intervals):
    ls = list(intervals)
    for v in ls:
        assert ls.index(v) == intervals.index(v)


@example(intervals=IntervalSet(((1, 1),)), v=0)
@example(intervals=IntervalSet(()), v=0)
@given(intervals(), st.integers(0, 0x10FFFF))
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


@st.composite
def overlapping_interval_lists(draw, max_codepoint=200):
    """Two interval lists whose sets are guaranteed to intersect.

    The old test generated both lists independently and used
    ``assume(not xs.isdisjoint(ys))``; under the crosshair backend every
    example failed that filter (459/459), making the test flaky in CI.
    Building the overlap in by construction keeps the same coverage without
    relying on a filter that the backends may never satisfy.
    """
    x = draw(interval_lists(min_size=1, max_codepoint=max_codepoint))
    shared = draw(st.sampled_from(sorted(intervals_to_set(x))))
    y_pairs = draw(
        st.lists(
            st.tuples(st.integers(0, max_codepoint), st.integers(0, max_codepoint))
        )
    )
    y_pairs = [tuple(sorted(pair)) for pair in y_pairs]
    y_pairs.append((shared, shared))
    return x, sorted(set(y_pairs))


@example(([(0, 1), (3, 3)], [(1, 3)]))
@example(([(0, 1)], [(0, 0), (1, 1)]))
@example(([(0, 1)], [(1, 1)]))
@given(overlapping_interval_lists(max_codepoint=200))
def test_subtraction_of_intervals(pair):
    x, y = pair
    xs = intervals_to_set(x)
    ys = intervals_to_set(y)
    assert not xs.isdisjoint(ys)  # guaranteed by the strategy, kept as an invariant
    z = IntervalSet(x).difference(IntervalSet(y)).intervals
    assert z == tuple(sorted(z))
    for a, b in z:
        assert a <= b
    assert intervals_to_set(z) == intervals_to_set(x) - intervals_to_set(y)


@given(intervals(max_codepoint=200), intervals(max_codepoint=200))
def test_interval_intersection(x, y):
    assert set(x & y) == set(x) & set(y)
    assert set(x.intersection(y)) == set(x).intersection(y)


def test_char_in_shrink_order():
    xs = IntervalSet([(0, 256)])
    assert xs[xs._idx_of_zero] == ord("0")
    assert xs[xs._idx_of_Z] == ord("Z")
    rewritten = [ord(xs.char_in_shrink_order(i)) for i in range(256)]
    assert rewritten != list(range(256))
    assert sorted(rewritten) == sorted(range(256))


def test_index_from_char_in_shrink_order():
    xs = IntervalSet([(0, 256)])
    for i in xs:
        assert xs.index_from_char_in_shrink_order(xs.char_in_shrink_order(i)) == i


def test_intervalset_equal():
    xs1 = IntervalSet([(0, 256)])
    xs2 = IntervalSet([(0, 256)])
    assert xs1 == xs2

    xs3 = IntervalSet([(0, 255)])
    assert xs2 != xs3
