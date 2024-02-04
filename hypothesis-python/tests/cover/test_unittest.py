# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import io
import sys
import unittest

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import FailedHealthCheck, HypothesisWarning

from tests.common.utils import fails_with, skipif_emscripten


class Thing_with_a_subThing(unittest.TestCase):
    """Example test case using subTest for the actual test below."""

    @given(st.tuples(st.booleans(), st.booleans()))
    def thing(self, lst):
        for i, b in enumerate(lst):
            with pytest.warns(HypothesisWarning):
                with self.subTest((i, b)):
                    self.assertTrue(b)


def test_subTest():
    suite = unittest.TestSuite()
    suite.addTest(Thing_with_a_subThing("thing"))
    stream = io.StringIO()
    out = unittest.TextTestRunner(stream=stream).run(suite)
    assert len(out.failures) <= out.testsRun, out


class test_given_on_setUp_fails_health_check(unittest.TestCase):
    @fails_with(FailedHealthCheck)
    @given(st.integers())
    def setUp(self, i):
        pass

    def test(self):
        """Provide something to set up for, so the setUp method is called."""


SUBTEST_SUITE = """
import unittest
from hypothesis import given, settings, strategies as st

class MyTest(unittest.TestCase):
    @given(s=st.text())
    @settings(deadline=None)
    def test_subtest(self, s):
        with self.subTest(text=s):
            self.assertIsInstance(s, str)

if __name__ == "__main__":
    unittest.main()
"""


@skipif_emscripten
@pytest.mark.parametrize("err", [[], ["-Werror"]])
def test_subTest_no_self(testdir, err):
    # https://github.com/HypothesisWorks/hypothesis/issues/2462
    # for some reason this issue happens only when running unittest from commandline
    fname = testdir.makepyfile(tests=SUBTEST_SUITE)
    result = testdir.run(sys.executable, *err, str(fname))
    expected = pytest.ExitCode.TESTS_FAILED if err else pytest.ExitCode.OK
    assert result.ret == expected, result.stderr.str()
