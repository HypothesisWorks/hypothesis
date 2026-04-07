# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import inspect
from unittest import TestCase

import pytest

from hypothesis import example, given
from hypothesis.strategies import booleans, integers


def test_must_use_result_of_test():
    class DoubleRun:
        def execute_example(self, function):
            x = function()
            if inspect.isfunction(x):
                return x()

        @given(booleans())
        def boom(self, b):
            def f():
                raise ValueError

            return f

    with pytest.raises(ValueError):
        DoubleRun().boom()


class TestTryReallyHard(TestCase):
    @given(integers())
    def test_something(self, i):
        pass

    def execute_example(self, f):
        f()
        return f()


class Valueless:
    def execute_example(self, f):
        try:
            return f()
        except ValueError:
            return None

    @given(integers())
    @example(1)
    def test_no_boom_on_example(self, x):
        raise ValueError

    @given(integers())
    def test_no_boom(self, x):
        raise ValueError

    @given(integers())
    def test_boom(self, x):
        raise AssertionError


def test_boom():
    with pytest.raises(AssertionError):
        Valueless().test_boom()


def test_no_boom():
    Valueless().test_no_boom()


def test_no_boom_on_example():
    Valueless().test_no_boom_on_example()
