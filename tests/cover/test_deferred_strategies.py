# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

from hypothesis import strategies as st
from tests.common.debug import minimal


def test_binary_tree():
    tree = st.deferred()
    tree.define(st.integers() | st.tuples(tree, tree))

    assert minimal(tree) == 0
    assert minimal(tree, lambda x: isinstance(x, tuple)) == (0, 0)


def test_bad_binary_tree():
    tree = st.deferred()
    tree.define(st.tuples(tree, tree) | st.integers())

    assert minimal(tree) == 0
    assert minimal(tree, lambda x: isinstance(x, tuple)) == (0, 0)


def test_large_branching_tree():
    tree = st.deferred()
    tree.define(st.integers() | st.tuples(tree, tree, tree, tree, tree))
    assert minimal(tree) == 0
    assert minimal(tree, lambda x: isinstance(x, tuple)) == (0,) * 5


def test_bad_branching_tree():
    tree = st.deferred()
    tree.define(st.tuples(tree, tree, tree, tree, tree) | st.integers())
    assert minimal(tree) == 0
    assert minimal(tree, lambda x: isinstance(x, tuple)) == (0,) * 5


def test_mutual_recursion():
    a = st.deferred()
    b = st.deferred()

    a.define(st.none() | st.tuples(st.just('a'), b))
    b.define(st.none() | st.tuples(st.just('b'), a))

    for c in ('a', 'b'):
        assert minimal(
            a | b, lambda x: x is not None and x[0] == c) == (c, None)


def test_non_trivial_json():
    json = st.deferred()

    lists = st.lists(json)
    objects = st.dictionaries(st.text(), json)

    json.define(
        st.none() | st.floats() | st.text() | lists | objects
    )

    assert minimal(json) is None

    small_list = minimal(json, lambda x: isinstance(x, list) and x)
    assert small_list == [None]

    x = minimal(
        json, lambda x: isinstance(x, dict) and isinstance(x.get(''), list))

    assert x == {'': []}
