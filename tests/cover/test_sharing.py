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

import hypothesis.strategies as st
from hypothesis import find, given

x = st.shared(st.integers())


@given(x, x)
def test_sharing_is_by_instance_by_default(a, b):
    assert a == b


@given(
    st.shared(st.integers(), key='hi'), st.shared(st.integers(), key='hi'))
def test_different_instances_with_the_same_key_are_shared(a, b):
    assert a == b


def test_different_instances_are_not_shared():
    find(
        st.tuples(st.shared(st.integers()), st.shared(st.integers())),
        lambda x: x[0] != x[1]
    )


def test_different_keys_are_not_shared():
    find(
        st.tuples(
            st.shared(st.integers(), key=1),
            st.shared(st.integers(), key=2)),
        lambda x: x[0] != x[1]
    )


def test_keys_and_default_are_not_shared():
    find(
        st.tuples(
            st.shared(st.integers(), key=1),
            st.shared(st.integers())),
        lambda x: x[0] != x[1]
    )


def test_can_simplify_shared_lists():
    xs = find(
        st.lists(st.shared(st.integers())),
        lambda x: len(x) >= 10 and x[0] != 0
    )
    assert xs == [1] * 10


def test_simplify_shared_linked_to_size():
    xs = find(
        st.lists(st.shared(st.integers())),
        lambda t: sum(t) >= 1000
    )
    assert sum(xs[:-1]) < 1000
    assert (xs[0] - 1) * len(xs) < 1000
