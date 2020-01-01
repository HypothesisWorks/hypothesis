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

from hypothesis import given
from hypothesis.internal.detection import is_hypothesis_test
from hypothesis.stateful import RuleBasedStateMachine, rule
from hypothesis.strategies import integers


def test_functions_default_to_not_tests():
    def foo():
        pass

    assert not is_hypothesis_test(foo)


def test_methods_default_to_not_tests():
    class Foo:
        def foo():
            pass

    assert not is_hypothesis_test(Foo().foo)


def test_detection_of_functions():
    @given(integers())
    def test(i):
        pass

    assert is_hypothesis_test(test)


def test_detection_of_methods():
    class Foo:
        @given(integers())
        def test(self, i):
            pass

    assert is_hypothesis_test(Foo().test)


def test_detection_of_stateful_tests():
    class Stuff(RuleBasedStateMachine):
        @rule(x=integers())
        def a_rule(self, x):
            pass

    assert is_hypothesis_test(Stuff.TestCase().runTest)
