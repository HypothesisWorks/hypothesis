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
from random import Random

from hypothesis.internal.conjecture.shrinking import Lexical


def test_shrink_to_zero():
    assert Lexical.shrink(bytes([255] * 8), lambda x: True) == bytes(8)


def test_shrink_to_smallest():
    assert Lexical.shrink(bytes([255] * 8), lambda x: sum(x) > 10) == bytes(
        [0] * 7 + [11]
    )


def test_float_hack_fails():
    assert Lexical.shrink(bytes([255] * 8), lambda x: x[0] >> 7) == bytes(
        [128] + [0] * 7
    )


def test_can_sort_bytes_by_reordering():
    start = bytes([5, 4, 3, 2, 1, 0])
    finish = Lexical.shrink(start, lambda x: set(x) == set(start))
    assert finish == bytes([0, 1, 2, 3, 4, 5])


def test_can_sort_bytes_by_reordering_partially():
    start = bytes([5, 4, 3, 2, 1, 0])
    finish = Lexical.shrink(start, lambda x: set(x) == set(start) and x[0] > x[-1])
    assert finish == bytes([1, 2, 3, 4, 5, 0])


def test_can_sort_bytes_by_reordering_partially2():
    start = bytes([5, 4, 3, 2, 1, 0])
    finish = Lexical.shrink(
        start,
        lambda x: Counter(x) == Counter(start) and x[0] > x[2],
        random=Random(0),
        full=True,
    )
    assert finish <= bytes([1, 2, 0, 3, 4, 5])


def test_can_sort_bytes_by_reordering_partially_not_cross_stationary_element():
    start = bytes([5, 3, 0, 2, 1, 4])
    finish = Lexical.shrink(start, lambda x: set(x) == set(start) and x[3] == 2)
    assert finish <= bytes([0, 3, 5, 2, 1, 4])
