# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from random import Random

from flaky import flaky

import hypothesis.strategies as st
from hypothesis import find, given, example, settings
from hypothesis.internal.debug import timeout
from hypothesis.internal.compat import integer_types


def test_can_generate_with_large_branching():
    def flatten(x):
        if isinstance(x, list):
            return sum(map(flatten, x), [])
        else:
            return [x]

    xs = find(
        st.recursive(
            st.integers(), lambda x: st.lists(x, average_size=50),
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
    xs = find(
        st.recursive(st.integers(), lambda x: st.lists(x, average_size=100)),
        lambda x: depth(x) > 1
    )
    assert xs in ([0], [[]])


def test_can_find_quite_broad_lists():
    def breadth(x):
        if isinstance(x, list):
            return sum(map(breadth, x))
        else:
            return 1

    broad = find(
        st.recursive(st.booleans(), lambda x: st.lists(x, max_size=10)),
        lambda x: breadth(x) >= 20,
        settings=settings(max_examples=10000)
    )
    assert breadth(broad) == 20


def test_drawing_many_near_boundary():
    ls = find(
        st.lists(st.recursive(
            st.booleans(),
            lambda x: st.lists(x, min_size=8, max_size=10).map(tuple),
            max_leaves=9)),
        lambda x: len(set(x)) >= 5,
        settings=settings(max_examples=10000, database=None, max_shrinks=2000)
    )
    assert len(ls) == 5


@given(st.randoms())
@settings(max_examples=50, max_shrinks=0)
@example(Random(-1363972488426139))
@example(Random(-4))
def test_can_use_recursive_data_in_sets(rnd):
    nested_sets = st.recursive(
        st.booleans(),
        lambda js: st.frozensets(js, average_size=2.0),
        max_leaves=10
    )
    nested_sets.example(rnd)

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
    x = find(
        nested_sets, lambda x: len(flatten(x)) == 2, random=rnd,
        settings=settings(database=None, max_shrinks=1000, max_examples=1000))
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
    xs = find(trees, lambda x: len(x) >= 10, settings=settings(
        database=None, timeout=20, max_shrinks=1000, max_examples=1000
    ))
    assert len(xs) == 10


@given(st.randoms())
@settings(max_examples=2, database=None)
@timeout(60)
def test_can_flatmap_to_recursive_data(rnd):
    stuff = st.lists(st.integers(), min_size=1).flatmap(
        lambda elts: st.recursive(
            st.sampled_from(elts), lambda x: st.lists(x, average_size=25),
            max_leaves=25
        ))

    def flatten(x):
        if isinstance(x, integer_types):
            return [x]
        else:
            return sum(map(flatten, x), [])

    tree = find(
        stuff, lambda x: sum(flatten(x)) >= 100,
        settings=settings(
            database=None, max_shrinks=2000, max_examples=1000,
            timeout=20,
        ),
        random=rnd
    )
    flat = flatten(tree)
    assert (sum(flat) == 1000) or (len(set(flat)) == 1)
