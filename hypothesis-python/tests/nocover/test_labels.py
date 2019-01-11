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


def test_labels_are_cached():
    x = st.integers()
    assert x.label is x.label


def test_labels_are_distinct():
    assert st.integers().label != st.text().label


@st.composite
def foo(draw):
    pass


@st.composite
def bar(draw):
    pass


def test_different_composites_have_different_labels():
    assert foo().label != bar().label


def test_one_of_label_is_distinct():
    a = st.integers()
    b = st.booleans()
    assert st.one_of(a, b).label != st.one_of(b, a).label


def test_lists_label_by_element():
    assert st.lists(st.integers()).label != st.lists(st.booleans()).label


def test_label_of_deferred_strategy_is_well_defined():
    recursive = st.deferred(lambda: st.lists(recursive))
    recursive.label
