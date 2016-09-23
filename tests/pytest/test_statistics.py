# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

from hypothesis.extra.pytestplugin import PRINT_STATISTICS_OPTION

pytest_plugins = 'pytester'


TESTSUITE = """
from hypothesis import given, settings, assume
from hypothesis.strategies import integers
import time


@given(integers())
def test_all_valid(x):
    pass


@settings(timeout=0.2, min_satisfying_examples=1)
@given(integers())
def test_slow(x):
    time.sleep(0.1)


@settings(max_examples=1000, min_satisfying_examples=1)
@given(integers())
def test_iterations(x):
    assume(x % 50 == 0)
"""


def test_does_not_run_statistics_by_default(testdir):
    script = testdir.makepyfile(TESTSUITE)
    result = testdir.runpytest(script)
    out = '\n'.join(result.stdout.lines)
    assert 'Hypothesis Statistics' not in out


def test_prints_statistics_given_option(testdir):
    script = testdir.makepyfile(TESTSUITE)
    result = testdir.runpytest(script, PRINT_STATISTICS_OPTION)
    out = '\n'.join(result.stdout.lines)
    assert 'Hypothesis Statistics' in out
    assert 'timeout=0.2' in out
    assert 'max_examples=200' in out
    assert 'max_iterations=1000' in out


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
    out = '\n'.join(result.stdout.lines)
    assert 'Hypothesis Statistics' in out
    assert 'max_examples=200' in out
