# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

from flaky import flaky

import hypothesis.strategies as st
from hypothesis import HealthCheck, given, settings
from tests.common.debug import minimal, find_any
from tests.common.utils import no_shrink


def test_can_generate_with_large_branching():
    def flatten(x):
        if isinstance(x, list):
            return sum(map(flatten, x), [])
        else:
            return [x]

    xs = minimal(
        st.recursive(
            st.integers(), lambda x: st.lists(x, min_size=25),
            max_leaves=100),
        lambda x: isinstance(x, list) and len(flatten(x)) >= 50
    )
    assert flatten(xs) == [0] * 50


def test_can_generate_some_depth_with_large_branching():
    def depth(x):
        if x and isinstance(x, list):
            return 1 + max(map(depth, x))
        else:
            return 1
    xs = minimal(
        st.recursive(st.integers(), st.lists),
        lambda x: depth(x) > 1
    )
    assert xs in ([0], [[]])


def test_can_find_quite_broad_lists():
    def breadth(x):
        if isinstance(x, list):
            return sum(map(breadth, x))
        else:
            return 1

    broad = minimal(
        st.recursive(st.booleans(), lambda x: st.lists(x, max_size=10)),
        lambda x: breadth(x) >= 20,
        settings=settings(max_examples=10000)
    )
    assert breadth(broad) == 20


def test_drawing_many_near_boundary():
    ls = minimal(
        st.lists(st.recursive(
            st.booleans(),
            lambda x: st.lists(x, min_size=8, max_size=10).map(tuple),
            max_leaves=9)),
        lambda x: len(set(x)) >= 5,
        settings=settings(max_examples=10000, database=None)
    )
    assert len(ls) == 5


@given(st.randoms())
@settings(
    max_examples=50, phases=no_shrink, suppress_health_check=HealthCheck.all(),
    deadline=None
)
def test_can_use_recursive_data_in_sets(rnd):
    nested_sets = st.recursive(st.booleans(), st.frozensets, max_leaves=3)
    find_any(nested_sets, random=rnd)

    def flatten(x):
        if isinstance(x, bool):
            return frozenset((x,))
        else:
            result = frozenset()
            for t in x:
                result |= flatten(t)
                if len(result) == 2:
                    break
            return result
    assert rnd is not None
    x = minimal(
        nested_sets, lambda x: len(flatten(x)) == 2, random=rnd,
        settings=settings(database=None, max_examples=1000))
    assert x in (
        frozenset((False, True)),
        frozenset((False, frozenset((True,)))),
        frozenset((frozenset((False, True)),))
    )


@flaky(max_runs=2, min_passes=1)
def test_can_form_sets_of_recursive_data():
    trees = st.sets(st.recursive(
        st.booleans(),
        lambda x: st.lists(x, min_size=5).map(tuple),
        max_leaves=20))
    xs = minimal(trees, lambda x: len(x) >= 5, settings=settings(
        database=None, max_examples=1000
    ))
    assert len(xs) == 5
