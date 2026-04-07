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


TEST_EXCEPTIONGROUP = """
from hypothesis import given, strategies as st

@given(x=st.booleans())
def test_fuzz_sorted(x):
    raise ValueError if x else TypeError
"""


@pytest.mark.parametrize("tb", ["auto", "long", "short", "native"])
def test_no_missing_reports(testdir, tb):
    script = testdir.makepyfile(TEST_EXCEPTIONGROUP)
    result = testdir.runpytest(script, f"--tb={tb}")
    out = "\n".join(result.stdout.lines)
    # If the False case is missing, that means we're not printing exception info.
    # See https://github.com/HypothesisWorks/hypothesis/issues/3430  With --tb=native,
    # we should show the full ExceptionGroup with *both* errors.
    assert "x=False" in out
    assert "x=True" in out or tb != "native"
