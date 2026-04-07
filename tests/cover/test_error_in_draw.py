# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import HypothesisWarning
from hypothesis.stateful import RuleBasedStateMachine, rule, run_state_machine_as_test


def test_error_is_in_finally():
    @given(st.data())
    def test(d):
        try:
            d.draw(st.lists(st.integers(), min_size=3, unique=True))
        finally:
            raise ValueError

    with pytest.raises(ValueError) as err:
        test()

    assert "[0, 1, -1]" in "\n".join(err.value.__notes__)


@given(st.data())
def test_warns_on_bool_strategy(data):
    with pytest.warns(
        HypothesisWarning,
        match=r"bool\(.+\) is always True, did you mean to draw a value\?",
    ):
        if st.booleans():  # 'forgot' to draw from the strategy
            pass


def test_adds_note_showing_which_strategy():
    class X:
        def __init__(self, y: int) -> None:
            assert y == 7

    @given(...)
    def inner(value: X):
        assert isinstance(value, X)

    rep = re.escape(repr(st.from_type(X)))
    with pytest.raises(AssertionError, match=f".*while generating 'value' from {rep}"):
        inner()


def test_adds_note_showing_which_strategy_stateful():
    strategy = st.integers().map(lambda x: x / 0)

    class Machine(RuleBasedStateMachine):
        @rule(value=strategy)
        def take_a_step(self, value):
            assert value

    msg = f"while generating 'value' from {strategy!r} for rule take_a_step"
    print(msg)
    with pytest.raises(ZeroDivisionError, match=f".*{re.escape(msg)}"):
        run_state_machine_as_test(Machine)
