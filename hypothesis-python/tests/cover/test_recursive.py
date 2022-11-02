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

from tests.common.debug import find_any, minimal

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument

@given(st.recursive(st.booleans(), st.lists, max_leaves=10))
def test_respects_leaf_limit(xs):
    def flatten(x):
        if isinstance(x, list):
            return sum(map(flatten, x), [])
        return [x]

    assert len(flatten(xs)) <= 10


def test_can_find_nested():
    x = minimal(
        st.recursive(st.booleans(), lambda x: st.tuples(x, x)),
        lambda x: isinstance(x, tuple) and isinstance(x[0], tuple),
    )

    assert x == ((False, False), False)


def test_recursive_call_validates_expand_returns_strategies():
    with pytest.raises(InvalidArgument):
        st.recursive(st.booleans(), lambda x: 1).example()


def test_recursive_call_validates_base_is_strategy():
    x = st.recursive(1, lambda x: st.none())
    with pytest.raises(InvalidArgument):
        x.example()


def test_can_find_exactly_max_leaves():
    strat = st.recursive(st.none(), lambda x: st.tuples(x, x), max_leaves=5)

    def enough_leaves(t):
        print(t)
        count = 0
        stack = [t]
        while stack:
            s = stack.pop()
            if s is None:
                count += 1
            else:
                stack.extend(s)
        return count >= 5

    find_any(strat, enough_leaves)


@given(st.recursive(st.none(), lambda x: st.tuples(x, x), max_leaves=1))
def test_can_exclude_branching_with_max_leaves(t):
    assert t is None


@given(st.recursive(st.none(), lambda x: st.one_of(x, x)))
def test_issue_1502_regression(s):
    pass
