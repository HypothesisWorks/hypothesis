# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import math

import pytest

from hypothesis import assume, given, strategies as st
from hypothesis.internal.conjecture.dfa import ConcreteDFA
from hypothesis.internal.conjecture.dfa.index import DFAIndex
from hypothesis.internal.conjecture.shrinker import sort_key


@st.composite
def dfas(draw):
    states = draw(st.integers(1, 5))

    a_state = st.integers(0, states - 1)
    a_byte = st.integers(0, 255)

    start = draw(a_state)
    accepting = draw(st.sets(a_state, min_size=1))

    transitions = [draw(st.dictionaries(a_byte, a_state),) for _ in range(states)]

    return ConcreteDFA(transitions, accepting, start)


def test_dfa_index_of_self_loop():
    # Matches strings of all zeroes of any length
    dfa = ConcreteDFA([{0: 0}], {0})

    index = DFAIndex(dfa)
    assert index.length() == math.inf

    for i in range(10):
        assert index[i] == bytes(i)
        assert index.index(bytes(i)) == i


def test_negative_index_not_supported():
    index = DFAIndex(ConcreteDFA([{}], {0}))
    with pytest.raises(IndexError):
        index[-1]


def test_value_error_for_non_matching():
    index = DFAIndex(ConcreteDFA([{0: 1}, {}], {1}))
    with pytest.raises(ValueError):
        index.index(b"")


def test_dfa_index_only_of_empty_string():
    dfa = ConcreteDFA([{}], {0})

    index = DFAIndex(dfa)

    assert len(index) == 1
    assert index[0] == b""


def test_eg_1():
    x = ConcreteDFA([{0: 1, 1: 1}, {0: 0}], {0})
    index = DFAIndex(x)

    assert index.length() == math.inf
    assert index[0] == b""
    assert index[1] == b"\0\0"
    assert index[2] == b"\1\0"
    assert index[3] == b"\0\0\0\0"
    assert index[4] == b"\0\0\1\0"


@given(dfas())
def test_dfa_iteration_order_agrees(dfa):
    assume(not dfa.is_dead(dfa.start))

    indexer = DFAIndex(dfa)

    assert indexer.length() > 0

    for i, x in enumerate(indexer):
        assert indexer[i] == x
        assert indexer.index(x) == i
        if i == 10:
            break


def test_raises_index_error_for_out_of_index():
    dfa = ConcreteDFA([{0: 1, 1: 1}, {}], {1})

    with pytest.raises(IndexError):
        DFAIndex(dfa)[2]


@given(dfas(), st.data())
def test_indexer_is_in_shortlex_order(dfa, data):
    assume(not dfa.is_dead(dfa.start))
    indexer = DFAIndex(dfa)

    assert indexer.length() > 0

    n = min(100, indexer.length() - 1)
    i = data.draw(st.integers(0, n))
    j = data.draw(st.integers(0, n))
    assume(i != j)

    i, j = sorted((i, j))

    assert sort_key(indexer[i]) < sort_key(indexer[j])
