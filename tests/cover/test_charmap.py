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

import os
import sys
import unicodedata

import pytest

import hypothesis.strategies as st
import hypothesis.internal.charmap as cm
from hypothesis import given, assume
from hypothesis.internal.compat import hunichr


def test_charmap_contains_all_unicode():
    n = 0
    for vs in cm.charmap().values():
        for u, v in vs:
            n += (v - u + 1)
    assert n == sys.maxunicode + 1


def test_charmap_has_right_categories():
    for cat, intervals in cm.charmap().items():
        for u, v in intervals:
            for i in range(u, v + 1):
                real = unicodedata.category(hunichr(i))
                assert real == cat, \
                    '%d is %s but reported in %s' % (i, real, cat)


def assert_valid_range_list(ls):
    for u, v in ls:
        assert u <= v
    for i in range(len(ls) - 1):
        assert ls[i] <= ls[i + 1]
        assert ls[i][-1] < ls[i + 1][0]


@given(
    st.sets(st.sampled_from(cm.categories())),
    st.sets(st.sampled_from(cm.categories())) | st.none(),
)
def test_query_matches_categories(exclude, include):
    values = cm.query(exclude, include)
    assert_valid_range_list(values)
    for u, v in values:
        for i in (u, v, (u + v) // 2):
            cat = unicodedata.category(hunichr(i))
            if include is not None:
                assert cat in include
            assert cat not in exclude


@given(
    st.sets(st.sampled_from(cm.categories())),
    st.sets(st.sampled_from(cm.categories())) | st.none(),
    st.integers(0, sys.maxunicode), st.integers(0, sys.maxunicode),
)
def test_query_matches_categories_codepoints(exclude, include, m1, m2):
    m1, m2 = sorted((m1, m2))
    values = cm.query(exclude, include, min_codepoint=m1, max_codepoint=m2)
    assert_valid_range_list(values)
    for u, v in values:
        assert m1 <= u
        assert v <= m2


@given(st.sampled_from(cm.categories()), st.integers(0, sys.maxunicode))
def test_exclude_only_excludes_from_that_category(cat, i):
    c = hunichr(i)
    assume(unicodedata.category(c) != cat)
    intervals = cm.query(exclude_categories=(cat,))
    assert any(a <= i <= b for a, b in intervals)


def test_reload_charmap():
    x = cm.charmap()
    assert x is cm.charmap()
    cm._charmap = None
    y = cm.charmap()
    assert x is not y
    assert x == y


def test_recreate_charmap():
    x = cm.charmap()
    assert x is cm.charmap()
    cm._charmap = None
    os.unlink(cm.charmap_file())
    y = cm.charmap()
    assert x is not y
    assert x == y


def test_union_empty():
    assert cm._union_interval_lists([], [[1, 2]]) == [[1, 2]]
    assert cm._union_interval_lists([[1, 2]], []) == [[1, 2]]


def test_successive_union():
    x = []
    for v in cm.charmap().values():
        x = cm._union_interval_lists(x, v)
    assert x == ((0, sys.maxunicode),)


def test_can_handle_race_between_exist_and_create(monkeypatch):
    x = cm.charmap()
    cm._charmap = None
    monkeypatch.setattr(os.path, 'exists', lambda p: False)
    y = cm.charmap()
    assert x is not y
    assert x == y


def test_exception_in_write_does_not_lead_to_broken_charmap(monkeypatch):
    def broken(*args, **kwargs):
        raise ValueError()

    cm._charmap = None
    monkeypatch.setattr(os.path, 'exists', lambda p: False)
    monkeypatch.setattr(os, 'rename', broken)
    with pytest.raises(ValueError):
        cm.charmap()

    with pytest.raises(ValueError):
        cm.charmap()
