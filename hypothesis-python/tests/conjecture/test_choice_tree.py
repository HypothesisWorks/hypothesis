# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import hypothesis.strategies as st
from hypothesis import given
from hypothesis.internal.compat import hrange
from hypothesis.internal.conjecture.choicetree import ChoiceTree


def exhaust(f):
    tree = ChoiceTree()

    results = []

    prefix = ()

    while not tree.exhausted:
        prefix = tree.step(prefix, lambda chooser: results.append(f(chooser)))
    return results


@given(st.lists(st.integers()))
def test_can_enumerate_a_shallow_set(ls):
    results = exhaust(lambda chooser: chooser.choose(ls))

    assert sorted(results) == sorted(ls)


def test_can_enumerate_a_nested_set():
    @exhaust
    def nested(chooser):
        i = chooser.choose(hrange(10))
        j = chooser.choose(hrange(10), condition=lambda j: j > i)
        return (i, j)

    assert sorted(nested) == [(i, j) for i in hrange(10) for j in hrange(i + 1, 10)]


def test_can_enumerate_empty():
    @exhaust
    def empty(chooser):
        return 1

    assert empty == [1]


def test_all_filtered_child():
    @exhaust
    def all_filtered(chooser):
        chooser.choose(hrange(10), condition=lambda j: False)

    assert all_filtered == []


def test_skips_over_exhausted_children():

    results = []

    def f(chooser):
        results.append(
            (
                chooser.choose(hrange(3), condition=lambda x: x > 0),
                chooser.choose(hrange(2)),
            )
        )

    tree = ChoiceTree()

    tree.step((1, 0), f)
    tree.step((1, 1), f)
    tree.step((0, 0), f)

    assert results == [(1, 0), (1, 1), (2, 0)]


def test_wraps_around_to_beginning():
    def f(chooser):
        chooser.choose(hrange(3))

    tree = ChoiceTree()

    assert tree.step((2,), f) == ()
