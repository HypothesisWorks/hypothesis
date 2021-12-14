# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from unittest import TestCase

import pytest

from hypothesis import find, given, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.stateful import RuleBasedStateMachine, rule


def test_cannot_use_without_a_runner():
    @given(st.runner())
    def f(x):
        pass

    with pytest.raises(InvalidArgument):
        f()


def test_cannot_use_in_find_without_default():
    with pytest.raises(InvalidArgument):
        find(st.runner(), lambda x: True)


def test_is_default_in_find():
    t = object()
    assert find(st.runner(default=t), lambda x: True) == t


@given(st.runner(default=1))
def test_is_default_without_self(runner):
    assert runner == 1


class TestStuff(TestCase):
    @given(st.runner())
    def test_runner_is_self(self, runner):
        assert runner is self

    @given(st.runner(default=3))
    def test_runner_is_self_even_with_default(self, runner):
        assert runner is self


class RunnerStateMachine(RuleBasedStateMachine):
    @rule(runner=st.runner())
    def step(self, runner):
        assert runner is self


TestState = RunnerStateMachine.TestCase
