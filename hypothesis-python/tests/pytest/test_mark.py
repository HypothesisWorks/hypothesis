# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

pytest_plugins = "pytester"


TESTSUITE = """
from hypothesis import given
from hypothesis.strategies import integers

@given(integers())
def test_foo(x):
    pass

def test_bar():
    pass
"""


def test_can_select_mark(testdir):
    script = testdir.makepyfile(TESTSUITE)
    result = testdir.runpytest(
        script, "--verbose", "--strict-markers", "-m", "hypothesis"
    )
    out = "\n".join(result.stdout.lines)
    assert "1 passed, 1 deselected" in out


UNITTEST_TESTSUITE = """
from hypothesis import given
from hypothesis.strategies import integers
from unittest import TestCase

class TestStuff(TestCase):
    @given(integers())
    def test_foo(self, x):
        pass

    def test_bar(self):
        pass
"""


def test_can_select_mark_on_unittest(testdir):
    script = testdir.makepyfile(UNITTEST_TESTSUITE)
    result = testdir.runpytest(
        script, "--verbose", "--strict-markers", "-m", "hypothesis"
    )
    out = "\n".join(result.stdout.lines)
    assert "1 passed, 1 deselected" in out
