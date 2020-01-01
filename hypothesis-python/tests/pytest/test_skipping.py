# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import pytest

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
    # going and raise a MultipleFailures error.  Ah well.
    else:
        assert xs == 0
"""


@pytest.mark.skipif(
    pytest.__version__.startswith("3.0"),
    reason="Pytest 3.0 predates a Skipped exception type, so we can't hook into it.",
)
def test_no_falsifying_example_if_pytest_skip(testdir):
    """If ``pytest.skip() is called during a test, Hypothesis should not
    continue running the test and shrink process, nor should it print anything
    about falsifying examples."""
    script = testdir.makepyfile(PYTEST_TESTSUITE)
    result = testdir.runpytest(script, "--verbose", "--strict", "-m", "hypothesis")
    out = "\n".join(result.stdout.lines)
    assert "Falsifying example" not in out
