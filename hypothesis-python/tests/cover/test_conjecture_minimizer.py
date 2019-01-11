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

from collections import Counter
from random import Random

from hypothesis.internal.compat import hbytes
from hypothesis.internal.conjecture.shrinking import Lexical


def test_shrink_to_zero():
    assert Lexical.shrink(
        hbytes([255] * 8), lambda x: True, random=Random(0)
    ) == hbytes(8)


def test_shrink_to_smallest():
    assert Lexical.shrink(
        hbytes([255] * 8), lambda x: sum(x) > 10, random=Random(0)
    ) == hbytes([0] * 7 + [11])


def test_float_hack_fails():
    assert Lexical.shrink(
        hbytes([255] * 8), lambda x: x[0] >> 7, random=Random(0)
    ) == hbytes([128] + [0] * 7)


def test_can_sort_bytes_by_reordering():
    start = hbytes([5, 4, 3, 2, 1, 0])
    finish = Lexical.shrink(start, lambda x: set(x) == set(start), random=Random(0))
    assert finish == hbytes([0, 1, 2, 3, 4, 5])


def test_can_sort_bytes_by_reordering_partially():
    start = hbytes([5, 4, 3, 2, 1, 0])
    finish = Lexical.shrink(
        start, lambda x: set(x) == set(start) and x[0] > x[-1], random=Random(0)
    )
    assert finish == hbytes([1, 2, 3, 4, 5, 0])


def test_can_sort_bytes_by_reordering_partially2():
    start = hbytes([5, 4, 3, 2, 1, 0])
    finish = Lexical.shrink(
        start,
        lambda x: Counter(x) == Counter(start) and x[0] > x[2],
        random=Random(0),
        full=True,
    )
    assert finish <= hbytes([1, 2, 0, 3, 4, 5])


def test_can_sort_bytes_by_reordering_partially_not_cross_stationary_element():
    start = hbytes([5, 3, 0, 2, 1, 4])
    finish = Lexical.shrink(
        start, lambda x: set(x) == set(start) and x[3] == 2, random=Random(0)
    )
    assert finish <= hbytes([0, 3, 5, 2, 1, 4])
