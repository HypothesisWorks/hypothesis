# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from collections import Counter

import pytest

from hypothesis.internal.conjecture.shrinking import (
    Bytes,
    Collection,
    Integer,
    Ordering,
    String,
)
from hypothesis.internal.intervalsets import IntervalSet


def test_shrink_to_zero():
    assert Integer.shrink(2**16, lambda n: True) == 0


def test_shrink_to_smallest():
    assert Integer.shrink(2**16, lambda n: n > 10) == 11


def test_can_sort_bytes_by_reordering():
    start = bytes([5, 4, 3, 2, 1, 0])
    finish = Ordering.shrink(start, lambda x: set(x) == set(start))
    assert bytes(finish) == bytes([0, 1, 2, 3, 4, 5])


def test_can_sort_bytes_by_reordering_partially():
    start = bytes([5, 4, 3, 2, 1, 0])
    finish = Ordering.shrink(start, lambda x: set(x) == set(start) and x[0] > x[-1])
    assert bytes(finish) == bytes([1, 2, 3, 4, 5, 0])


def test_can_sort_bytes_by_reordering_partially2():
    start = bytes([5, 4, 3, 2, 1, 0])
    finish = Ordering.shrink(
        start,
        lambda x: Counter(x) == Counter(start) and x[0] > x[2],
        full=True,
    )
    assert bytes(finish) == bytes([1, 2, 0, 3, 4, 5])


def test_can_sort_bytes_by_reordering_partially_not_cross_stationary_element():
    start = bytes([5, 3, 0, 2, 1, 4])
    finish = Ordering.shrink(start, lambda x: set(x) == set(start) and x[3] == 2)
    assert bytes(finish) == bytes([0, 1, 3, 2, 4, 5])


@pytest.mark.parametrize(
    "initial, predicate, intervals, expected",
    [
        ("f" * 10, lambda s: True, IntervalSet.from_string("abcdefg"), ""),
        ("f" * 10, lambda s: len(s) >= 3, IntervalSet.from_string("abcdefg"), "aaa"),
        (
            "f" * 10,
            lambda s: len(s) >= 3 and "a" not in s,
            IntervalSet.from_string("abcdefg"),
            "bbb",
        ),
    ],
)
def test_shrink_strings(initial, predicate, intervals, expected):
    assert String.shrink(
        initial, predicate, intervals=intervals, min_size=len(expected)
    ) == tuple(expected)


@pytest.mark.parametrize(
    "initial, predicate, expected",
    [
        (b"\x18\x12", lambda v: len(v) == 2, b"\x00\x00"),
        (b"\x18\x12", lambda v: True, b""),
        (b"\x01\x10", lambda v: len(v) > 0 and v[0] == 1, b"\x01"),
        (b"\x01\x10\x01\x92", lambda v: sum(v) >= 9, b"\x09"),
    ],
)
def test_shrink_bytes(initial, predicate, expected):
    assert bytes(Bytes.shrink(initial, predicate, min_size=len(expected))) == expected


def test_collection_left_is_better():
    shrinker = Collection(
        [1, 2, 3], lambda v: True, ElementShrinker=Integer, min_size=3
    )
    assert not shrinker.left_is_better([1, 2, 3], [1, 2, 3])
