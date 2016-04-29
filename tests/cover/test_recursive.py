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

import pytest

import hypothesis.strategies as st
from hypothesis import find, given
from hypothesis.errors import InvalidArgument


@given(
    st.recursive(
        st.booleans(), lambda x: st.lists(x, average_size=20),
        max_leaves=10))
def test_respects_leaf_limit(xs):
    def flatten(x):
        if isinstance(x, list):
            return sum(map(flatten, x), [])
        else:
            return [x]
    assert len(flatten(xs)) <= 10


def test_can_find_nested():
    x = find(
        st.recursive(st.booleans(), lambda x: st.tuples(x, x)),
        lambda x: isinstance(x, tuple) and isinstance(x[0], tuple)
    )

    assert x == ((False, False), False)


def test_recursive_call_validates_expand_returns_strategies():
    with pytest.raises(InvalidArgument):
        st.recursive(st.booleans(), lambda x: 1).example()
