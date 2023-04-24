# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from _hypothesis_pytestplugin import PRINT_STATISTICS_OPTION

pytest_plugins = "pytester"


def get_output(testdir, suite, *args):
    script = testdir.makepyfile(suite)
    result = testdir.runpytest(script, *args)
    return "\n".join(result.stdout.lines)


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


@settings(max_examples=100, suppress_health_check=list(HealthCheck))
@given(integers())
def test_iterations(x):
    assume(x == 13)
"""


def test_does_not_run_statistics_by_default(testdir):
    out = get_output(testdir, TESTSUITE)
    assert "Hypothesis Statistics" not in out


def test_prints_statistics_given_option(testdir):
    out = get_output(testdir, TESTSUITE, PRINT_STATISTICS_OPTION)
    assert "Hypothesis Statistics" in out
    assert "max_examples=100" in out
    assert "< 10% of examples satisfied assumptions" in out


def test_prints_statistics_given_option_under_xdist(testdir):
    out = get_output(testdir, TESTSUITE, PRINT_STATISTICS_OPTION, "-n", "2")
    assert "Hypothesis Statistics" in out
    assert "max_examples=100" in out
    assert "< 10% of examples satisfied assumptions" in out


def test_prints_statistics_given_option_with_junitxml(testdir):
    out = get_output(testdir, TESTSUITE, PRINT_STATISTICS_OPTION, "--junit-xml=out.xml")
    assert "Hypothesis Statistics" in out
    assert "max_examples=100" in out
    assert "< 10% of examples satisfied assumptions" in out


@pytest.mark.skipif(
    tuple(map(int, pytest.__version__.split(".")[:2])) < (5, 4), reason="too old"
)
def test_prints_statistics_given_option_under_xdist_with_junitxml(testdir):
    out = get_output(
        testdir, TESTSUITE, PRINT_STATISTICS_OPTION, "-n", "2", "--junit-xml=out.xml"
    )
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
