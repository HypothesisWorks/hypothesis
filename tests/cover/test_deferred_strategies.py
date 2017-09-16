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

import pytest

from hypothesis import strategies as st
from hypothesis import given
from hypothesis.errors import InvalidArgument
from tests.common.debug import minimal, assert_no_examples


def test_binary_tree():
    tree = st.deferred(lambda: st.integers() | st.tuples(tree, tree))

    assert minimal(tree) == 0
    assert minimal(tree, lambda x: isinstance(x, tuple)) == (0, 0)


def test_bad_binary_tree():
    tree = st.deferred(lambda: st.tuples(tree, tree) | st.integers())

    assert minimal(tree) == 0
    assert minimal(tree, lambda x: isinstance(x, tuple)) == (0, 0)


def test_large_branching_tree():
    tree = st.deferred(
        lambda: st.integers() | st.tuples(tree, tree, tree, tree, tree))
    assert minimal(tree) == 0
    assert minimal(tree, lambda x: isinstance(x, tuple)) == (0,) * 5


def test_bad_branching_tree():
    tree = st.deferred(
        lambda: st.tuples(tree, tree, tree, tree, tree) | st.integers())
    assert minimal(tree) == 0
    assert minimal(tree, lambda x: isinstance(x, tuple)) == (0,) * 5


def test_mutual_recursion():
    t = st.deferred(lambda: a | b)
    a = st.deferred(lambda: st.none() | st.tuples(st.just('a'), b))
    b = st.deferred(lambda: st.none() | st.tuples(st.just('b'), a))

    for c in ('a', 'b'):
        assert minimal(
            t, lambda x: x is not None and x[0] == c) == (c, None)


def test_non_trivial_json():
    json = st.deferred(
        lambda: st.none() | st.floats() | st.text() | lists | objects
    )

    lists = st.lists(json)
    objects = st.dictionaries(st.text(), json)

    assert minimal(json) is None

    small_list = minimal(json, lambda x: isinstance(x, list) and x)
    assert small_list == [None]

    x = minimal(
        json, lambda x: isinstance(x, dict) and isinstance(x.get(''), list))

    assert x == {'': []}


def test_errors_on_non_function_define():
    x = st.deferred(1)
    with pytest.raises(InvalidArgument):
        x.example()


def test_errors_if_define_does_not_return_search_strategy():
    x = st.deferred(lambda: 1)
    with pytest.raises(InvalidArgument):
        x.example()


def test_errors_on_definition_as_self():
    x = st.deferred(lambda: x)
    with pytest.raises(InvalidArgument):
        x.example()


def test_branches_pass_through_deferred():
    x = st.one_of(st.booleans(), st.integers())
    y = st.deferred(lambda: x)
    assert x.branches == y.branches


def test_can_draw_one_of_self():
    x = st.deferred(lambda: st.one_of(st.booleans(), x))
    assert minimal(x) is False
    assert len(x.branches) == 1


def test_hidden_self_references_just_result_in_no_example():
    bad = st.deferred(lambda: st.none().flatmap(lambda _: bad))
    assert_no_examples(bad)


def test_self_recursive_flatmap():
    bad = st.deferred(lambda: bad.flatmap(lambda x: st.none()))
    assert_no_examples(bad)


def test_self_reference_through_one_of_can_detect_emptiness():
    bad = st.deferred(lambda: st.one_of(bad, bad))
    assert bad.is_empty


def test_self_tuple_draws_nothing():
    x = st.deferred(lambda: st.tuples(x))
    assert_no_examples(x)


def test_mutually_recursive_tuples_draw_nothing():
    x = st.deferred(lambda: st.tuples(y))
    y = st.tuples(x)

    assert_no_examples(x)
    assert_no_examples(y)


def test_self_recursive_lists():
    x = st.deferred(lambda: st.lists(x))
    assert minimal(x) == []
    assert minimal(x, bool) == [[]]
    assert minimal(x, lambda x: len(x) > 1) == [[], []]


def test_literals_strategy_is_valid():
    literals = st.deferred(lambda: st.one_of(
        st.booleans(),
        st.tuples(literals, literals),
        literals.map(lambda x: [x]),
    ))

    @given(literals)
    def test(e):
        pass
    test()

    assert not literals.has_reusable_values
