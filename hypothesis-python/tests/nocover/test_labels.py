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

from hypothesis import strategies as st
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.strategies._internal.lazy import LazyStrategy


def test_labels_are_cached():
    x = st.integers()
    assert x.label is x.label


def test_labels_are_distinct():
    assert st.integers().label != st.text().label


@st.composite
def foo(draw):
    return draw(st.none())


@st.composite
def bar(draw):
    return draw(st.none())


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


@pytest.mark.parametrize(
    "strategy",
    [
        lambda: [st.none()],
        lambda: [st.integers()],
        lambda: [st.lists(st.floats())],
        lambda: [st.none(), st.integers(), st.lists(st.floats())],
    ],
)
def test_sampled_from_label_with_strategies_does_not_change(strategy):
    s1 = st.sampled_from(strategy())
    s2 = st.sampled_from(strategy())
    assert s1.label == s2.label


def test_label_of_enormous_sampled_range():
    # this should not take forever.
    st.sampled_from(range(2**30)).label


@pytest.mark.parametrize(
    "strategy",
    [
        lambda: st.deferred(lambda: st.integers()),
        lambda: LazyStrategy(st.integers, (), {}),
    ],
)
def test_draw_uses_wrapped_label(strategy):
    cd = ConjectureData.for_choices([0])
    strategy = strategy()
    cd.draw(strategy)
    cd.freeze()

    assert len(cd.spans) == 2
    assert cd.spans[1].label == st.integers().label


def test_deferred_label():
    strategy = st.deferred(lambda: st.integers())
    assert strategy.label != st.integers().label
