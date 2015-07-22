# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
import hypothesis.strategies as st
from hypothesis import find
from hypothesis.errors import InvalidArgument


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
        st.recursive(st.booleans(), lambda x: 1)
