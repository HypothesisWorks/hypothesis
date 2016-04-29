# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from unittest import TestCase

import pytest

from hypothesis import strategies as st
from hypothesis import find, given
from hypothesis.errors import InvalidArgument
from hypothesis.stateful import GenericStateMachine


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
    assert find(st.runner(t), lambda x: True) == t


@given(st.runner(1))
def test_is_default_without_self(runner):
    assert runner == 1


class TestStuff(TestCase):

    @given(st.runner())
    def test_runner_is_self(self, runner):
        assert runner is self

    @given(st.runner(default=3))
    def test_runner_is_self_even_with_default(self, runner):
        assert runner is self


class RunnerStateMachine(GenericStateMachine):

    def steps(self):
        return st.runner()

    def execute_step(self, step):
        assert self is step

TestState = RunnerStateMachine.TestCase
