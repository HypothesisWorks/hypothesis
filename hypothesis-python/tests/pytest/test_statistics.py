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

from distutils.version import LooseVersion

import pytest

from hypothesis.extra.pytestplugin import PRINT_STATISTICS_OPTION

pytest_plugins = "pytester"


TESTSUITE = """
from hypothesis import HealthCheck, given, settings, assume
from hypothesis.strategies import integers
import time
import warnings
from hypothesis.errors import HypothesisDeprecationWarning

warnings.simplefilter('always', HypothesisDeprecationWarning)


@given(integers())
def test_all_valid(x):
    pass


@settings(max_examples=100, suppress_health_check=HealthCheck.all())
@given(integers())
def test_iterations(x):
    assume(x == 13)
"""


def test_does_not_run_statistics_by_default(testdir):
    script = testdir.makepyfile(TESTSUITE)
    result = testdir.runpytest(script)
    out = "\n".join(result.stdout.lines)
    assert "Hypothesis Statistics" not in out


def test_prints_statistics_given_option(testdir):
    script = testdir.makepyfile(TESTSUITE)
    result = testdir.runpytest(script, PRINT_STATISTICS_OPTION)
    out = "\n".join(result.stdout.lines)
    assert "Hypothesis Statistics" in out
    assert "max_examples=100" in out
    assert "< 10% of examples satisfied assumptions" in out


@pytest.mark.skipif(LooseVersion(pytest.__version__) < "3.5", reason="too old")
def test_prints_statistics_given_option_under_xdist(testdir):
    script = testdir.makepyfile(TESTSUITE)
    result = testdir.runpytest(script, PRINT_STATISTICS_OPTION, "-n", "2")
    out = "\n".join(result.stdout.lines)
    assert "Hypothesis Statistics" in out
    assert "max_examples=100" in out
    assert "< 10% of examples satisfied assumptions" in out


UNITTEST_TESTSUITE = """

from hypothesis import given
from hypothesis.strategies import integers
from unittest import TestCase


class TestStuff(TestCase):
    @given(integers())
    def test_all_valid(self, x):
        pass
"""


def test_prints_statistics_for_unittest_tests(testdir):
    script = testdir.makepyfile(UNITTEST_TESTSUITE)
    result = testdir.runpytest(script, PRINT_STATISTICS_OPTION)
    out = "\n".join(result.stdout.lines)
    assert "Hypothesis Statistics" in out
    assert "TestStuff::test_all_valid" in out
    assert "max_examples=100" in out


STATEFUL_TESTSUITE = """
from hypothesis.stateful import RuleBasedStateMachine, rule

class Stuff(RuleBasedStateMachine):
    @rule()
    def step(self):
        pass

TestStuff = Stuff.TestCase
"""


def test_prints_statistics_for_stateful_tests(testdir):
    script = testdir.makepyfile(STATEFUL_TESTSUITE)
    result = testdir.runpytest(script, PRINT_STATISTICS_OPTION)
    out = "\n".join(result.stdout.lines)
    assert "Hypothesis Statistics" in out
    assert "TestStuff::runTest" in out
    assert "max_examples=100" in out
