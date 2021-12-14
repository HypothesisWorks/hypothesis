# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

pytest_plugins = "pytester"


TESTSUITE = """
from hypothesis import given
from hypothesis.strategies import lists, integers

@given(integers())
def test_this_one_is_ok(x):
    pass

@given(lists(integers()))
def test_hi(xs):
    assert False
"""


def test_runs_reporting_hook(testdir):
    script = testdir.makepyfile(TESTSUITE)
    result = testdir.runpytest(script, "--verbose")
    out = "\n".join(result.stdout.lines)
    assert "test_this_one_is_ok" in out
    assert "Captured stdout call" not in out
    assert "Falsifying example" in out
    assert result.ret != 0
