# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import pytest

from hypothesis import assume, given, settings
from hypothesis.strategies import integers, text


class HasSetup(object):
    def setup_example(self):
        self.setups = getattr(self, u"setups", 0)
        self.setups += 1


class HasTeardown(object):
    def teardown_example(self, ex):
        self.teardowns = getattr(self, u"teardowns", 0)
        self.teardowns += 1


class SomeGivens(object):
    @given(integers())
    def give_me_an_int(self, x):
        pass

    @given(text())
    def give_me_a_string(myself, x):
        pass

    @given(integers())
    @settings(max_examples=1000)
    def give_me_a_positive_int(self, x):
        assert x >= 0

    @given(integers().map(lambda x: x.nope))
    def fail_in_reify(self, x):
        pass

    @given(integers())
    def assume_some_stuff(self, x):
        assume(x > 0)

    @given(integers().filter(lambda x: x > 0))
    def assume_in_reify(self, x):
        pass


class HasSetupAndTeardown(HasSetup, HasTeardown, SomeGivens):
    pass


def test_calls_setup_and_teardown_on_self_as_first_argument():
    x = HasSetupAndTeardown()
    x.give_me_an_int()
    x.give_me_a_string()
    assert x.setups > 0
    assert x.teardowns == x.setups


def test_calls_setup_and_teardown_on_self_unbound():
    x = HasSetupAndTeardown()
    HasSetupAndTeardown.give_me_an_int(x)
    assert x.setups > 0
    assert x.teardowns == x.setups


def test_calls_setup_and_teardown_on_failure():
    x = HasSetupAndTeardown()
    with pytest.raises(AssertionError):
        x.give_me_a_positive_int()
    assert x.setups > 0
    assert x.teardowns == x.setups


def test_still_tears_down_on_error_in_generation():
    x = HasSetupAndTeardown()
    with pytest.raises(AttributeError):
        x.fail_in_reify()
    assert x.setups > 0
    assert x.teardowns == x.setups


def test_still_tears_down_on_failed_assume():
    x = HasSetupAndTeardown()
    x.assume_some_stuff()
    assert x.setups > 0
    assert x.teardowns == x.setups


def test_still_tears_down_on_failed_assume_in_reify():
    x = HasSetupAndTeardown()
    x.assume_in_reify()
    assert x.setups > 0
    assert x.teardowns == x.setups


def test_sets_up_without_teardown():
    class Foo(HasSetup, SomeGivens):
        pass

    x = Foo()
    x.give_me_an_int()
    assert x.setups > 0
    assert not hasattr(x, u"teardowns")


def test_tears_down_without_setup():
    class Foo(HasTeardown, SomeGivens):
        pass

    x = Foo()
    x.give_me_an_int()
    assert x.teardowns > 0
    assert not hasattr(x, u"setups")
