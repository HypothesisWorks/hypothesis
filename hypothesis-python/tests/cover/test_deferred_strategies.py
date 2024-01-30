# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument

from tests.common.debug import assert_no_examples, check_can_generate_examples, minimal


def test_binary_tree():
    tree = st.deferred(lambda: st.integers() | st.tuples(tree, tree))

    assert minimal(tree) == 0
    assert minimal(tree, lambda x: isinstance(x, tuple)) == (0, 0)


def test_mutual_recursion():
    t = st.deferred(lambda: a | b)
    a = st.deferred(lambda: st.none() | st.tuples(st.just("a"), b))
    b = st.deferred(lambda: st.none() | st.tuples(st.just("b"), a))

    for c in ("a", "b"):
        assert minimal(t, lambda x: x is not None and x[0] == c) == (c, None)  # noqa


def test_errors_on_non_function_define():
    x = st.deferred(1)
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(x)


def test_errors_if_define_does_not_return_search_strategy():
    x = st.deferred(lambda: 1)
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(x)


def test_errors_on_definition_as_self():
    x = st.deferred(lambda: x)
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(x)


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


def test_literals_strategy_is_valid():
    literals = st.deferred(
        lambda: st.one_of(
            st.booleans(), st.tuples(literals, literals), literals.map(lambda x: [x])
        )
    )

    @given(literals)
    def test(e):
        pass

    test()

    assert not literals.has_reusable_values


def test_impossible_self_recursion():
    x = st.deferred(lambda: st.tuples(st.none(), x))
    assert x.is_empty
    assert x.has_reusable_values


def test_very_deep_deferral():
    # This test is designed so that the recursive properties take a very long
    # time to converge: Although we can rapidly determine them for the original
    # value, each round in the fixed point calculation only manages to update
    # a single value in the related strategies, so it takes 100 rounds to
    # update everything. Most importantly this triggers our infinite loop
    # detection heuristic and we start tracking duplicates, but we shouldn't
    # see any because this loop isn't infinite, just long.
    def strat(i):
        if i == 0:
            return st.deferred(lambda: st.one_of([*strategies, st.none()]))
        else:
            return st.deferred(lambda: st.tuples(strategies[(i + 1) % len(strategies)]))

    strategies = list(map(strat, range(100)))

    assert strategies[0].has_reusable_values
    assert not strategies[0].is_empty


def test_recursion_in_middle():
    # This test is significant because the integers().map(abs) is not checked
    # in the initial pass - when we recurse into x initially we decide that
    # x is empty, so the tuple is empty, and don't need to check the third
    # argument. Then when we do the more refined test we've discovered that x
    # is non-empty, so we need to check the non-emptiness of the last component
    # to determine the non-emptiness of the tuples.
    x = st.deferred(lambda: st.tuples(st.none(), x, st.integers().map(abs)) | st.none())
    assert not x.is_empty


def test_deferred_supports_find():
    nested = st.deferred(lambda: st.integers() | st.lists(nested))
    assert nested.supports_find
