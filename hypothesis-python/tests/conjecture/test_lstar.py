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

import pytest

from hypothesis import assume, example, given, strategies as st
from hypothesis.errors import InvalidState
from hypothesis.internal.conjecture.dfa.lstar import IntegerNormalizer, LStar


def test_can_learn_simple_predicate():
    learner = LStar(lambda s: len(s) >= 3)

    learner.learn(bytes(3))

    dfa = learner.dfa
    assert dfa.start == 0
    assert dfa.transition(0, 0) == 1
    assert dfa.transition(1, 0) == 2
    assert dfa.transition(2, 0) == 3
    assert dfa.transition(3, 0) == 3

    assert not dfa.is_accepting(0)
    assert not dfa.is_accepting(1)
    assert not dfa.is_accepting(2)
    assert dfa.is_accepting(3)


def test_relearning_does_not_change_generation():
    learner = LStar(lambda s: len(s) >= 3)

    prev = learner.generation
    learner.learn(bytes(3))
    assert prev != learner.generation

    prev = learner.generation
    learner.learn(bytes(3))
    assert prev == learner.generation


def test_can_learn_dead_nodes():
    learner = LStar(lambda s: len(s) == 4 and max(s) <= 1)

    learner.learn(bytes(4))

    assert learner.dfa.matches(bytes(4))
    assert learner.dfa.matches(bytes([1] * 4))
    assert learner.dfa.matches(bytes([1] * 4))

    learner.learn([2, 0, 0, 0])

    # Need a length 5 string to distinguish this from
    # something that just loops back to zero.
    learner.learn([2, 0, 0, 0, 0])

    dfa = learner.dfa

    assert dfa.is_dead(dfa.transition(dfa.start, 2))
    assert dfa.is_dead(dfa.transition(dfa.start, 3))


def test_iterates_over_learned_strings():
    upper_bound = bytes([1, 2])
    learner = LStar(lambda s: len(s) == 2 and max(s) <= 5 and s <= upper_bound)

    learner.learn(upper_bound)

    prev = -1
    while learner.generation != prev:
        prev = learner.generation
        learner.learn([1, 2, 0])
        learner.learn([6, 1, 2])
        learner.learn([1, 3])
        for i in range(7):
            learner.learn([0, i])
            learner.learn([1, i])
        learner.learn([2, 0])

        learner.learn([2, 0, 0, 0])
        learner.learn([2, 0, 0])
        learner.learn([0, 6, 0, 0])
        learner.learn([1, 3, 0, 0])
        learner.learn([1, 6, 0, 0])
        learner.learn([0, 0, 0, 0, 0])

    dfa = learner.dfa

    n = 9
    matches = list(itertools.islice(dfa.all_matching_strings(), n + 1))
    for m in matches:
        assert learner.member(m), list(m)
    assert len(matches) == n


def test_iteration_with_dead_nodes():
    learner = LStar(lambda s: len(s) == 3 and max(s) <= 1 and s[1] == 0)
    learner.learn([1, 0, 1])
    learner.learn([1, 1, 1])
    learner.learn([0, 1, 1])
    learner.learn([1, 1, 0])
    learner.learn([1, 1, 1, 0, 1])
    learner.learn([0, 0, 4])

    dfa = learner.dfa
    i = dfa.transition(dfa.start, 1)
    assert not dfa.is_dead(i)
    assert dfa.is_dead(dfa.transition(i, 2))

    assert list(learner.dfa.all_matching_strings()) == [
        bytes([0, 0, 0]),
        bytes([0, 0, 1]),
        bytes([1, 0, 0]),
        bytes([1, 0, 1]),
    ]


def test_learning_is_just_checking_when_fully_explored():
    count = 0

    def accept(s):
        nonlocal count
        count += 1
        return len(s) <= 5 and all(c == 0 for c in s)

    learner = LStar(accept)

    for c in [0, 1]:
        for n in range(10):
            learner.learn(bytes([c]) * n)

    assert list(learner.dfa.all_matching_strings()) == [bytes(n) for n in range(6)]

    prev = count

    learner.learn([2] * 11)

    calls = count - prev

    assert calls == 1


def test_canonicalises_values_to_zero_where_appropriate():
    calls = 0

    def member(s):
        nonlocal calls
        calls += 1
        return len(s) == 10

    learner = LStar(member)

    learner.learn(bytes(10))
    learner.learn(bytes(11))

    prev = calls

    assert learner.dfa.matches(bytes([1] * 10))

    assert calls == prev


def test_normalizing_defaults_to_zero():
    normalizer = IntegerNormalizer()

    assert normalizer.normalize(10) == 0

    assert not normalizer.distinguish(10, lambda n: True)

    assert normalizer.normalize(10) == 0


def test_normalizing_can_be_made_to_distinguish_values():
    normalizer = IntegerNormalizer()

    assert normalizer.distinguish(10, lambda n: n >= 5)
    assert normalizer.normalize(10) == 5
    assert normalizer.normalize(4) == 0


def test_learning_large_dfa():
    """Mostly the thing this is testing is actually that this runs in reasonable
    time. A naive breadth first search will run ~forever when trying to find this
    because it will have to explore all strings of length 19 before it finds one
    of length 20."""

    learner = LStar(lambda s: len(s) == 20)

    learner.learn(bytes(20))

    for i, s in enumerate(itertools.islice(learner.dfa.all_matching_strings(), 500)):
        assert len(s) == 20
        assert i == int.from_bytes(s, "big")


def varint_predicate(b):
    if not b:
        return False
    n = b[0] & 15
    if len(b) != n + 1:
        return False
    value = int.from_bytes(b[1:], "big")
    return value >= 10


@st.composite
def varint(draw):
    result = bytearray()
    result.append(draw(st.integers(1, 255)))
    n = result[0] & 15
    assume(n > 0)
    value = draw(st.integers(10, 256**n - 1))
    result.extend(value.to_bytes(n, "big"))
    return bytes(result)


@example([b"\x02\x01\n"])
@given(st.lists(varint(), min_size=1))
def test_can_learn_varint_predicate(varints):
    learner = LStar(varint_predicate)
    prev = -1
    while learner.generation != prev:
        prev = learner.generation

        for s in varints:
            learner.learn(s)

    for s in varints:
        assert learner.dfa.matches(s)


def test_cannot_reuse_dfa():
    x = LStar(lambda x: len(x) == 3)
    dfa = x.dfa
    x.learn(bytes(3))
    with pytest.raises(InvalidState):
        dfa.start
