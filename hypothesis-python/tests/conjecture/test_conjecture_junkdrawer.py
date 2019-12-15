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

from hypothesis import example, given, strategies as st
from hypothesis.internal.conjecture.junkdrawer import LazySequenceCopy, clamp


def test_out_of_range():
    x = LazySequenceCopy([1, 2, 3])

    with pytest.raises(IndexError):
        x[3]

    with pytest.raises(IndexError):
        x[-4]


def test_pass_through():
    x = LazySequenceCopy([1, 2, 3])
    assert x[0] == 1
    assert x[1] == 2
    assert x[2] == 3


def test_can_assign_without_changing_underlying():
    underlying = [1, 2, 3]
    x = LazySequenceCopy(underlying)
    x[1] = 10
    assert x[1] == 10
    assert underlying[1] == 2


def test_pop():
    x = LazySequenceCopy([2, 3])
    assert x.pop() == 3
    assert x.pop() == 2

    with pytest.raises(IndexError):
        x.pop()


@example(1, 5, 10)
@example(1, 10, 5)
@example(5, 10, 5)
@example(5, 1, 10)
@given(st.integers(), st.integers(), st.integers())
def test_clamp(lower, value, upper):
    lower, upper = sorted((lower, upper))

    clamped = clamp(lower, value, upper)

    assert lower <= clamped <= upper

    if lower <= value <= upper:
        assert value == clamped
    if lower > value:
        assert clamped == lower
    if value > upper:
        assert clamped == upper
