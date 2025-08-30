# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import strategies as st
from hypothesis.internal.conjecture.junkdrawer import IntList
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

INTEGERS = st.integers(0, 2**68)


@st.composite
def valid_index(draw):
    machine = draw(st.runner())
    if not machine.model:
        return draw(st.nothing())
    return draw(st.integers(0, len(machine.model) - 1))


class IntListRules(RuleBasedStateMachine):
    @initialize(ls=st.lists(INTEGERS))
    def starting_lists(self, ls):
        self.model = list(ls)
        self.target = IntList(ls)

    @invariant()
    def lists_are_equivalent(self):
        if hasattr(self, "model"):
            assert isinstance(self.model, list)
            assert isinstance(self.target, IntList)
            assert len(self.model) == len(self.target)
            assert list(self.target) == self.model

    @rule(n=INTEGERS)
    def append(self, n):
        self.model.append(n)
        self.target.append(n)

    @rule(i=valid_index())
    def delete(self, i):
        del self.model[i]
        del self.target[i]

    @rule(i=valid_index())
    def agree_on_values(self, i):
        assert self.model[i] == self.target[i]


TestIntList = IntListRules.TestCase
