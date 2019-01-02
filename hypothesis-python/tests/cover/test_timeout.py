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
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import time

import pytest

from hypothesis import find, given, reject, settings
from hypothesis.errors import NoSuchExample, Timeout
from hypothesis.strategies import integers
from tests.common.utils import (
    checks_deprecated_behaviour,
    fails,
    fails_with,
    validate_deprecation,
)


def test_hitting_timeout_is_deprecated():
    with validate_deprecation():

        @settings(timeout=0.1)
        @given(integers())
        def test_slow_test_times_out(x):
            time.sleep(0.05)

    with validate_deprecation():
        test_slow_test_times_out()


def test_slow_unsatisfiable_test():
    with validate_deprecation():

        @settings(timeout=0.1)
        @given(integers())
        def test_slow_test_times_out(x):
            time.sleep(0.05)
            reject()

    with validate_deprecation():
        with pytest.raises(Timeout):
            test_slow_test_times_out()


# Cheap hack to make test functions which fail on their second invocation
calls = [0, 0, 0, 0]


with validate_deprecation():
    timeout_settings = settings(timeout=0.2)


# The following tests exist to test that verifiers start their timeout
# from when the test first executes, not from when it is defined.
@checks_deprecated_behaviour
@fails
@given(integers())
@timeout_settings
def test_slow_failing_test_1(x):
    time.sleep(0.05)
    assert not calls[0]
    calls[0] = 1


@checks_deprecated_behaviour
@fails
@timeout_settings
@given(integers())
def test_slow_failing_test_2(x):
    time.sleep(0.05)
    assert not calls[1]
    calls[1] = 1


@checks_deprecated_behaviour
@fails
@given(integers())
@timeout_settings
def test_slow_failing_test_3(x):
    time.sleep(0.05)
    assert not calls[2]
    calls[2] = 1


@checks_deprecated_behaviour
@fails
@timeout_settings
@given(integers())
def test_slow_failing_test_4(x):
    time.sleep(0.05)
    assert not calls[3]
    calls[3] = 1


with validate_deprecation():
    strict_timeout_settings = settings(timeout=60)


@checks_deprecated_behaviour
@strict_timeout_settings
@given(integers())
def test_deprecated_behaviour(i):
    time.sleep(100)


@checks_deprecated_behaviour
@fails_with(AssertionError)
@strict_timeout_settings
@given(integers())
def test_does_not_hide_errors_with_deprecation(i):
    time.sleep(100)
    assert False


def test_can_hit_timeout_in_find():
    def f(x):
        time.sleep(100)
        return x >= 100

    with pytest.raises(NoSuchExample):
        with validate_deprecation():
            find(integers(), f, settings=timeout_settings)
