# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

TESTSUITE = """
from hypothesis.stateful import RuleBasedStateMachine, rule

class FailingMachine(RuleBasedStateMachine):
    @rule()
    def my_rule(self):
        assert False

TestFailingMachine = FailingMachine.TestCase
"""


def test_internal_calls_suppressed(testdir):
    """
    Test to make sure that no internal calls are included in a failing
    test's traceback.
    """
    script = testdir.makepyfile(TESTSUITE)
    result = testdir.runpytest(script)
    out = '\n'.join(result.stdout.lines)
    assert 'stateful.py' not in out
