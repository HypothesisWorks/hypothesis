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


PYTEST_TESTSUITE = """
from hypothesis import given
from hypothesis.strategies import integers
import pytest

@given(xs=integers())
def test_to_be_skipped(xs):
    # We always try the simplest example first, raising a Skipped exception
    # which we know to propagate immediately...
    if xs == 0:
        pytest.skip()
    # But the pytest 3.0 internals don't have such an exception, so we keep
    # going and raise a BaseExceptionGroup error.  Ah well.
    else:
        assert xs == 0
"""


def test_no_falsifying_example_if_pytest_skip(testdir):
    """If ``pytest.skip() is called during a test, Hypothesis should not
    continue running the test and shrink process, nor should it print anything
    about falsifying examples."""
    script = testdir.makepyfile(PYTEST_TESTSUITE)
    result = testdir.runpytest(
        script, "--verbose", "--strict-markers", "-m", "hypothesis"
    )
    out = "\n".join(result.stdout.lines)
    assert "Falsifying example" not in out


def test_issue_3453_regression(testdir):
    """If ``pytest.skip() is called during a test, Hypothesis should not
    continue running the test and shrink process, nor should it print anything
    about falsifying examples."""
    script = testdir.makepyfile(
        """
from hypothesis import example, given, strategies as st
import pytest

@given(value=st.none())
@example("hello")
@example("goodbye")
def test_skip_on_first_skipping_example(value):
    assert value is not None
    assert value != "hello"  # queue up a non-skip error which must be discarded
    pytest.skip()
"""
    )
    result = testdir.runpytest(script, "--tb=native")
    result.assert_outcomes(skipped=1)
