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

import hypothesis.strategies as st
from hypothesis.internal.compat import hbytes
from hypothesis.internal.conjecture.data import Status, StructuralTag, \
    ConjectureData


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


def get_tags(strat, buf):
    d = ConjectureData.for_buffer(buf)
    d.draw(strat)
    d.freeze()
    assert d.status == Status.VALID
    return d.tags


def test_labels_get_used_for_tagging():
    assert get_tags(st.integers(), hbytes(8)) != get_tags(st.text(), hbytes(8))


def test_labels_get_used_for_tagging_branches():
    strat = st.one_of(
        st.booleans().map(lambda x: not x),
        st.booleans().map(lambda x: x),
    )

    assert get_tags(strat, hbytes(2)) != get_tags(strat, hbytes([1, 0]))


def run_for_labels(buffer):
    buffer = hbytes(buffer)

    def accept(f):
        data = ConjectureData.for_buffer(buffer)
        f(data)
        data.freeze()
        return frozenset(
            t.label for t in data.tags if isinstance(t, StructuralTag))
    return accept


def test_discarded_intervals_are_not_in_labels():
    @run_for_labels([0, 0])
    def x(data):
        data.start_example(3)
        data.draw_bits(1)
        data.stop_example(discard=True)
        data.start_example(2)
        data.draw_bits(1)
        data.stop_example()

    assert 3 not in x
    assert 2 in x


def test_nested_discarded_intervals_are_not_in_labels():
    @run_for_labels([0, 0, 0])
    def x(data):
        data.start_example(3)
        data.draw_bits(1)
        data.start_example(4)
        data.draw_bits(1)
        data.stop_example()
        data.stop_example(discard=True)
        data.start_example(2)
        data.draw_bits(1)
        data.stop_example()

    assert 2 in x
    assert 3 not in x
    assert 4 not in x


def test_label_of_deferred_strategy_is_well_defined():
    recursive = st.deferred(lambda: st.lists(recursive))
    recursive.label
