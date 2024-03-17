# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import itertools
import math
from math import inf

import pytest

from hypothesis import (
    HealthCheck,
    assume,
    example,
    given,
    note,
    reject,
    settings,
    strategies as st,
)
from hypothesis.internal.conjecture.dfa import DEAD, ConcreteDFA


def test_enumeration_when_sizes_do_not_agree():
    dfa = ConcreteDFA([{0: 1, 1: 2}, {}, {1: 3}, {}], {1, 3})  # 0  # 1  # 2  # 3

    assert list(dfa.all_matching_strings()) == [b"\0", b"\1\1"]


def test_enumeration_of_very_long_strings():
    """This test is mainly testing that it terminates. If we were
    to use a naive breadth first search for this it would take
    forever to run because it would run in time roughly 256 ** 50.
    """
    size = 50
    dfa = ConcreteDFA(
        [{c: n + 1 for c in range(256)} for n in range(100)] + [{}], {size}
    )

    for i, s in enumerate(dfa.all_matching_strings()):
        assert len(s) == size
        assert int.from_bytes(s, "big") == i
        if i >= 1000:
            break


def test_is_dead_with_cache_reuse():
    dfa = ConcreteDFA([{0: i + 1, 1: 11} for i in range(10)] + [{}, {}], {10})
    for n in range(10, -1, -1):
        assert not dfa.is_dead(n)


def test_max_length_of_empty_dfa_is_zero():
    dfa = ConcreteDFA([{}], {0})
    assert dfa.max_length(dfa.start) == 0


def test_mixed_dfa_initialization():
    d = ConcreteDFA([[(2, 1)], [(0, 5, 2)], {4: 0, 3: 1}], {0})

    assert d.transition(0, 2) == 1
    assert d.transition(0, 3) == DEAD

    for n in range(6):
        assert d.transition(1, n) == 2
    assert d.transition(1, 6) == DEAD

    assert d.transition(2, 4) == 0
    assert d.transition(2, 3) == 1
    assert d.transition(2, 5) == DEAD


@st.composite
def dfas(draw):
    states = draw(st.integers(1, 20))

    a_state = st.integers(0, states - 1)
    a_byte = st.integers(0, 255)

    start = draw(a_state)
    accepting = draw(st.sets(a_state, min_size=1))

    transitions = [draw(st.dictionaries(a_byte, a_state)) for _ in range(states)]

    return ConcreteDFA(transitions, accepting, start)


@settings(max_examples=20)
@given(dfas(), st.booleans())
@example(
    ConcreteDFA(
        transitions=[[(0, 2), (1, 255, 1)], [(0, 2), (1, 255, 0)], []],
        accepting={2},
    ),
    False,
)
def test_canonicalised_matches_same_strings(dfa, via_repr):
    canon = dfa.canonicalise()
    note(canon)

    if via_repr:
        canon = eval(repr(canon))

    assert dfa.max_length(dfa.start) == canon.max_length(canon.start)

    try:
        minimal = next(dfa.all_matching_strings())
    except StopIteration:
        reject()

    assert minimal == next(canon.all_matching_strings())

    assert dfa.count_strings(dfa.start, len(minimal)) == canon.count_strings(
        canon.start, len(minimal)
    )


# filters about 80% of examples. should potentially improve at some point.
@settings(max_examples=20, suppress_health_check=[HealthCheck.filter_too_much])
@given(dfas())
def test_has_string_of_max_length(dfa):
    length = dfa.max_length(dfa.start)
    assume(math.isfinite(length))
    assume(not dfa.is_dead(dfa.start))

    assert dfa.count_strings(dfa.start, length) > 0


def test_converts_long_tables_to_dicts():
    dfa = ConcreteDFA(
        [[(0, 0), (1, 1), (2, 2), (3, 1), (4, 0), (7, 10, 1)], [(0, 0)], []], {2}
    )
    assert dfa.transition(0, 2) == 2
    assert dfa.transition(1, 0) == 0

    assert isinstance(dfa._ConcreteDFA__transitions[0], dict)
    assert isinstance(dfa._ConcreteDFA__transitions[1], list)


@settings(max_examples=20)
@given(dfas(), dfas())
def test_dfa_with_different_string_is_not_equivalent(x, y):
    assume(not x.is_dead(x.start))

    s = next(x.all_matching_strings())
    assume(not y.matches(s))

    assert not x.equivalent(y)


@example(x=b"", y=b"\0", z=b"\0")
@given(x=st.binary(), y=st.binary(min_size=1), z=st.binary())
def test_all_matching_regions_include_all_matches(x, y, z):
    y_matcher = ConcreteDFA([{c: i + 1} for i, c in enumerate(y)] + [[]], {len(y)})
    assert y_matcher.matches(y)

    s = x + y + z

    assert (len(x), len(x) + len(y)) in y_matcher.all_matching_regions(s)


@pytest.mark.parametrize("n", [1, 10, 100, 1000])
def test_max_length_of_long_dfa(n):
    dfa = ConcreteDFA([{0: i + 1} for i in range(n)] + [{}], {n})
    assert not dfa.is_dead(dfa.start)
    assert dfa.max_length(dfa.start) == n


def test_dfa_with_cached_dead():
    dfa = ConcreteDFA([[{0: 1, 1: 2}], [], []], {2})

    assert dfa.is_dead(1)
    assert dfa.is_dead(0)


@pytest.mark.parametrize("order", itertools.permutations((0, 1, 2)))
def test_dead_nodes(order):
    dfa = ConcreteDFA([{0: 1, 1: 2}, {}, {}], {2})
    for i in order:
        assert dfa.is_dead(i) == (i == 1)


@given(st.permutations(range(5)))
def test_max_length_of_recursive_dfa(order):
    dfa = ConcreteDFA([{0: 1, 1: 2, 2: 3}, {0: 2}, {0: 1}, {0: 0, 1: 4}, {}], {4})
    for i in order:
        dfa.max_length(i)

    assert dfa.max_length(0) == inf
    assert dfa.max_length(1) == 0
    assert dfa.max_length(2) == 0
    assert dfa.max_length(3) == inf
    assert dfa.max_length(4) == 0


def test_transitions_out_of_dead_are_empty():
    dfa = ConcreteDFA([{}], {0})
    assert list(dfa.raw_transitions(DEAD)) == []


def test_can_transition_from_dead():
    dfa = ConcreteDFA([{}], {0})
    assert dfa.transition(DEAD, 0) == DEAD
