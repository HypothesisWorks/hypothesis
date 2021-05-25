# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

import hypothesis.strategies as st
from hypothesis import Phase, example, given, settings
from hypothesis.internal.conjecture.dfa.lstar import LStar


@st.composite
def byte_order(draw):
    ls = draw(st.permutations(range(256)))
    n = draw(st.integers(0, len(ls)))
    return ls[:n]


@example({0}, [1])
@given(st.sets(st.integers(0, 255)), byte_order())
# This test doesn't even use targeting at all, but for some reason the
# pareto optimizer makes it much slower.
@settings(phases=set(Phase) - {Phase.target})
def test_learning_always_changes_generation(chars, order):
    learner = LStar(lambda s: len(s) == 1 and s[0] in chars)
    for c in order:
        prev = learner.generation
        s = bytes([c])
        if learner.dfa.matches(s) != learner.member(s):
            learner.learn(s)
            assert learner.generation > prev
