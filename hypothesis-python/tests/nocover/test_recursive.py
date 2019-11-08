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

import hypothesis.strategies as st
from hypothesis import settings
from tests.common.debug import find_any, minimal
from tests.common.utils import flaky


def test_can_generate_with_large_branching():
    def flatten(x):
        if isinstance(x, list):
            return sum(map(flatten, x), [])
        else:
            return [x]

    size = 20

    xs = minimal(
        st.recursive(
            st.integers(),
            lambda x: st.lists(x, min_size=size // 2),
            max_leaves=size * 2,
        ),
        lambda x: isinstance(x, list) and len(flatten(x)) >= size,
        timeout_after=None,
    )
    assert flatten(xs) == [0] * size


def test_can_generate_some_depth_with_large_branching():
    def depth(x):
        if x and isinstance(x, list):
            return 1 + max(map(depth, x))
        else:
            return 1

    xs = minimal(
        st.recursive(st.integers(), st.lists),
        lambda x: depth(x) > 1,
        timeout_after=None,
    )
    assert xs in ([0], [[]])


def test_can_find_quite_broad_lists():
    def breadth(x):
        if isinstance(x, list):
            return sum(map(breadth, x))
        else:
            return 1

    target = 10

    broad = minimal(
        st.recursive(st.booleans(), lambda x: st.lists(x, max_size=target // 2)),
        lambda x: breadth(x) >= target,
        settings=settings(max_examples=10000),
        timeout_after=None,
    )
    assert breadth(broad) == target


def test_drawing_many_near_boundary():
    target = 4

    ls = minimal(
        st.lists(
            st.recursive(
                st.booleans(),
                lambda x: st.lists(
                    x, min_size=2 * (target - 1), max_size=2 * target
                ).map(tuple),
                max_leaves=2 * target - 1,
            )
        ),
        lambda x: len(set(x)) >= target,
        timeout_after=None,
    )
    assert len(ls) == target


def test_can_use_recursive_data_in_sets():
    nested_sets = st.recursive(st.booleans(), st.frozensets, max_leaves=3)
    find_any(nested_sets, settings=settings(deadline=None))

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

    x = minimal(nested_sets, lambda x: len(flatten(x)) == 2, settings(deadline=None))
    assert x in (
        frozenset((False, True)),
        frozenset((False, frozenset((True,)))),
        frozenset((frozenset((False, True)),)),
    )


@flaky(max_runs=2, min_passes=1)
def test_can_form_sets_of_recursive_data():
    size = 3

    trees = st.sets(
        st.recursive(
            st.booleans(),
            lambda x: st.lists(x, min_size=size).map(tuple),
            max_leaves=20,
        )
    )
    xs = minimal(trees, lambda x: len(x) >= size, timeout_after=None)
    assert len(xs) == size
