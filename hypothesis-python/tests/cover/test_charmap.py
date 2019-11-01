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

import os
import sys
import tempfile
import time
import unicodedata

import hypothesis.internal.charmap as cm
import hypothesis.strategies as st
from hypothesis import assume, given
from hypothesis.internal.compat import hunichr


def test_charmap_contains_all_unicode():
    n = 0
    for vs in cm.charmap().values():
        for u, v in vs:
            n += v - u + 1
    assert n == sys.maxunicode + 1


def test_charmap_has_right_categories():
    for cat, intervals in cm.charmap().items():
        for u, v in intervals:
            for i in range(u, v + 1):
                real = unicodedata.category(hunichr(i))
                assert real == cat, "%d is %s but reported in %s" % (i, real, cat)


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
    st.integers(0, sys.maxunicode),
    st.integers(0, sys.maxunicode),
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


def test_uses_cached_charmap():
    cm.charmap()

    # Reset the last-modified time of the cache file to a point in the past.
    mtime = int(time.time() - 1000)
    os.utime(cm.charmap_file(), (mtime, mtime))
    statinfo = os.stat(cm.charmap_file())
    assert statinfo.st_mtime == mtime

    # Force reload of charmap from cache file and check that mtime is unchanged.
    cm._charmap = None
    cm.charmap()
    statinfo = os.stat(cm.charmap_file())
    assert statinfo.st_mtime == mtime


def test_union_empty():
    assert cm._union_intervals([], []) == ()
    assert cm._union_intervals([], [[1, 2]]) == ((1, 2),)
    assert cm._union_intervals([[1, 2]], []) == ((1, 2),)


def test_union_handles_totally_overlapped_gap():
    #   < xx  >  Imagine the intervals x and y as bit strings.
    # | <yy yy>  The bit at position n is set if n falls inside that interval.
    # = <zzzzz>  In this model _union_intervals() performs bit-wise or.
    assert cm._union_intervals([[2, 3]], [[1, 2], [4, 5]]) == ((1, 5),)


def test_union_handles_partially_overlapped_gap():
    #   <  x  >  Imagine the intervals x and y as bit strings.
    # | <yy  y>  The bit at position n is set if n falls inside that interval.
    # = <zzz z>  In this model _union_intervals() performs bit-wise or.
    assert cm._union_intervals([[3, 3]], [[1, 2], [5, 5]]) == ((1, 3), (5, 5))


def test_successive_union():
    x = []
    for v in cm.charmap().values():
        x = cm._union_intervals(x, v)
    assert x == ((0, sys.maxunicode),)


def test_can_handle_race_between_exist_and_create(monkeypatch):
    x = cm.charmap()
    cm._charmap = None
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    y = cm.charmap()
    assert x is not y
    assert x == y


def test_exception_in_write_does_not_lead_to_broken_charmap(monkeypatch):
    def broken(*args, **kwargs):
        raise ValueError()

    cm._charmap = None
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    monkeypatch.setattr(os, "rename", broken)

    cm.charmap()
    cm.charmap()


def test_regenerate_broken_charmap_file():
    cm.charmap()
    file_loc = cm.charmap_file()

    with open(file_loc, "wb"):
        pass

    cm._charmap = None
    cm.charmap()


def test_exclude_characters_are_included_in_key():
    assert cm.query() != cm.query(exclude_characters="0")


def test_error_writing_charmap_file_is_suppressed(monkeypatch):
    def broken_mkstemp(dir):
        raise RuntimeError()

    monkeypatch.setattr(tempfile, "mkstemp", broken_mkstemp)

    try:
        # Cache the charmap to avoid a performance hit the next time
        # somebody tries to use it.
        saved = cm._charmap
        cm._charmap = None
        os.unlink(cm.charmap_file())

        cm.charmap()
    finally:
        cm._charmap = saved
