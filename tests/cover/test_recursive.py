# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import pytest

import hypothesis.strategies as st
from flaky import flaky
from hypothesis import find, given, Settings
from hypothesis.errors import InvalidArgument
from hypothesis.internal.debug import timeout
from hypothesis.internal.compat import integer_types


def test_can_generate_with_large_branching():
    xs = find(
        st.recursive(st.integers(), lambda x: st.lists(x, average_size=100)),
        lambda x: isinstance(x, list) and len(x) >= 50
    )
    assert xs == [0] * 50


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
    assert xs == [0]


def test_can_find_quite_deep_lists():
    def depth(x):
        if x and isinstance(x, list):
            return 1 + max(map(depth, x))
        else:
            return 1

    deep = find(
        st.recursive(st.booleans(), lambda x: st.lists(x, max_size=3)),
        lambda x: depth(x) >= 5)
    assert deep == [[[[False]]]]


def test_can_find_quite_broad_lists():
    def breadth(x):
        if isinstance(x, list):
            return sum(map(breadth, x))
        else:
            return 1

    broad = find(
        st.recursive(st.booleans(), lambda x: st.lists(x, max_size=10)),
        lambda x: breadth(x) >= 20)
    assert breadth(broad) == 20


def test_drawing_many_near_boundary():
    ls = find(
        st.lists(st.recursive(
            st.booleans(),
            lambda x: st.lists(x, min_size=8, max_size=10).map(tuple),
            max_leaves=9)),
        lambda x: len(set(x)) >= 5)
    assert len(ls) == 5


def test_recursive_call_validates_expand_returns_strategies():
    with pytest.raises(InvalidArgument):
        st.recursive(st.booleans(), lambda x: 1).example()


@given(st.randoms())
def test_can_use_recursive_data_in_sets(rnd):
    nested_sets = st.recursive(
        st.booleans(),
        lambda js: st.frozensets(js),
        max_leaves=10
    )
    nested_sets.example()

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
    x = find(
        nested_sets, lambda x: len(flatten(x)) == 2, random=rnd,
        settings=Settings(database=None))
    assert x == frozenset((False, True))


def test_can_form_sets_of_recursive_data():
    trees = st.sets(st.recursive(
        st.booleans(),
        lambda x: st.lists(x, min_size=5).map(tuple),
        max_leaves=10))
    xs = find(trees, lambda x: len(x) >= 10, settings=Settings(
        database=None
    ))
    print(xs)
    assert len(xs) == 10
    assert False in xs
    assert True in xs


@flaky(max_runs=5, min_passes=1)
@given(st.randoms(), settings=Settings(max_examples=10, database=None))
def test_can_simplify_hard_recursive_data_into_boolean_alternative(rnd):
    """This test forces us to exercise the simplification through redrawing
    functionality, thus testing that we can deal with bad templates."""
    def leaves(ls):
        if isinstance(ls, (bool,) + integer_types):
            return [ls]
        else:
            return sum(map(leaves, ls), [])

    def hard(base):
        return st.recursive(
            base, lambda x: st.lists(x, max_size=5), max_leaves=20)
    r = find(
        hard(st.booleans()) |
        hard(st.booleans()) |
        hard(st.booleans()) |
        hard(st.integers()) |
        hard(st.booleans()),
        lambda x: len(leaves(x)) >= 3,
        random=rnd, settings=Settings(database=None, max_examples=5000))
    lvs = leaves(r)
    assert lvs == [False] * 3
    assert all(isinstance(v, bool) for v in lvs), repr(lvs)


@flaky(max_runs=5, min_passes=1)
@given(st.randoms(), settings=Settings(max_examples=10, database=None))
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
        settings=Settings(database=None, max_shrinks=2000, max_examples=1000),
        random=rnd
    )
    flat = flatten(tree)
    assert (sum(flat) == 1000) or (len(set(flat)) == 1)
