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

from itertools import chain
from random import Random

import hypothesis.strategies as st
from hypothesis import example, given
from hypothesis.internal.compat import ceil, floor, hrange
from hypothesis.internal.conjecture.shrinking import Length
from tests.common.costbounds import find_integer_cost

sizes = st.integers(0, 100)


@example(m=0, n=1)
@given(sizes, sizes)
def test_shrinks_down_to_size(m, n):
    m, n = sorted((m, n))
    assert Length.shrink(
        [0] * n + [1], lambda ls: len(ls) >= m + 1 and ls[-1] == 1, random=Random(0)
    ) == (0,) * m + (1,)


def test_will_shrink_to_zero():
    assert Length.shrink([1], lambda x: True, random=Random(0)) == ()


def _concat(xs):
    return tuple(chain.from_iterable(xs))


@given(st.lists(st.integers(0, 20), min_size=1))
def test_deletes_all_easily_deletable_elements(gap_sizes):
    # For each "gap size" in the input, create that many 0s, followed by a 1.
    # Then remove the last 1, so that there can be a gap at the end.
    data = _concat([0] * g + [1] for g in gap_sizes)[:-1]
    total = sum(data)

    result = Length.shrink(data, lambda d: sum(d) == total, random=Random(0))

    # All 0s should have been deleted, leaving only the 1s.
    assert result == (1,) * total


@st.composite
def poison_problem(draw):
    list_length = draw(st.integers(1, 100))
    poison = draw(st.integers(0, list_length - 1))
    return draw(st.permutations(list(hrange(list_length)))), poison


@example(problem=([0, 1], 0))
@example(problem=([0, 1, 2, 3, 4, 5, 6, 7], 5))
@given(problem=poison_problem())
def test_gets_down_to_single_element_in_logarithmic_time(problem):
    """Fairly detailed cost analysis test that checks that the adaptive
    logic in length deletion is working properly."""

    indices, poison = problem

    class FakeRandom(object):
        def shuffle(self, ls):
            assert sorted(ls) == sorted(indices)
            ls[:] = indices

    cost = [0]

    def predicate(ls):
        cost[0] += 1
        return poison in ls

    Length.shrink(sorted(indices), predicate, random=FakeRandom())

    cost = cost[0]

    def halves(n):
        return [floor(n / 2), ceil(n / 2)]

    # The poison value splits the list into two halves. We then pick a
    # random index in each of these halves and clear to its left and to
    # its right using find_integer. This means we have four tests (the
    # check for the empty list, the check for the poison value, and the
    # check for each of the two random starting indices) plus the find_integer
    # cost for clearing each of the four segments.
    bound = 4 + sum(
        find_integer_cost(m2)
        for m1 in halves(len(indices) - 1)
        for m2 in halves(m1 - 1)
    )

    assert 0 < cost <= bound


def test_does_not_try_to_delete_endpoints():
    """This is a fairly specific test designed to check that the logic
    for not retrying end points is working correctly.

    We first try deleting 4. This works and causes us to try deleting
    4 and 3 together, which doesn't work because we require 3 to be
    present in the list. This should now cause us to mark 3 as required,
    and thus not attempt to delete it again in this run.
    """
    ls = [0, 1, 2, 3, 4]

    class FakeRandom(object):
        def shuffle(self, ls):
            ls[:] = [4, 0, 1, 2, 3]

    def predicate(x):
        if not x:
            return False
        x = list(x)
        assert 3 in x or x == ls[: len(x)]
        return 3 in x and len(x) >= 3

    Length.shrink(ls, predicate, random=FakeRandom())
