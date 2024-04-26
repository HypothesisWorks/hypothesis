# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import example, given, strategies as st
from hypothesis.internal.conjecture.shrinking import Ordering


@example([0, 1, 1, 1, 1, 1, 1, 0])
@example([0, 0])
@example([0, 1, -1])
@given(st.lists(st.integers()))
def test_shrinks_down_to_sorted_the_slow_way(ls):
    # We normally would short-circuit and find that we can sort this
    # automatically, but here we test that a single run_step could put the
    # list in sorted order anyway if it had to, and that that is just an
    # optimisation.
    shrinker = Ordering(ls, lambda ls: True, full=False)
    shrinker.run_step()
    assert list(shrinker.current) == sorted(ls)


def test_can_partially_sort_a_list():
    finish = Ordering.shrink([5, 4, 3, 2, 1, 0], lambda x: x[0] > x[-1])
    assert finish == (1, 2, 3, 4, 5, 0)


def test_can_partially_sort_a_list_2():
    finish = Ordering.shrink([5, 4, 3, 2, 1, 0], lambda x: x[0] > x[2], full=True)
    assert finish <= (1, 2, 0, 3, 4, 5)


def test_adaptively_shrinks_around_hole():
    initial = list(range(1000, 0, -1))
    initial[500] = 2000

    intended_result = sorted(initial)
    intended_result.insert(500, intended_result.pop())

    shrinker = Ordering(initial, lambda ls: ls[500] == 2000, full=True)
    shrinker.run()

    assert shrinker.current[500] == 2000

    assert list(shrinker.current) == intended_result
    assert shrinker.calls <= 60
