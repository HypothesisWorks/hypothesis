# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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


@pytest.mark.parametrize('s', [
    st.floats(),
    st.tuples(st.integers()),
    st.tuples(),
    st.one_of(st.integers(), st.text()),
])
def test_is_cacheable(s):
    assert s.is_cacheable


@pytest.mark.parametrize('s', [
    st.just([]),
    st.tuples(st.integers(), st.just([])),
    st.one_of(st.integers(), st.text(), st.just([])),
])
def test_is_not_cacheable(s):
    assert not s.is_cacheable


def test_non_cacheable_things_are_not_cached():
    x = st.just([])
    assert st.tuples(x) != st.tuples(x)


def test_cacheable_things_are_cached():
    x = st.just(())
    assert st.tuples(x) == st.tuples(x)
