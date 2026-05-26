# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re

import pytest

pytest_plugins = "pytester"


CONFTEST = """
import time
import hypothesis.internal.conjecture.providers as providers

_called = False

def slow_get_local_constants():
    global _called
    if not _called:
        _called = True
        time.sleep(0.1)
    return providers._local_constants

providers._get_local_constants = slow_get_local_constants
providers._sys_modules_len = None
"""


TESTSUITE = """
from hypothesis import given, Phase, settings
from hypothesis.strategies import integers
from hypothesis.internal.conjecture.providers import _get_local_constants

def test_first():
    # Force constant collection to happen during this test
    _get_local_constants()

@given(integers())
@settings(phases=[Phase.generate], max_examples=1, database=None)
def test_second(x):
    pass
"""


@pytest.mark.parametrize("plugin_disabled", [False, True])
def test_constant_collection_timing(testdir, plugin_disabled):
    # See https://github.com/HypothesisWorks/hypothesis/issues/4627
    testdir.makeconftest(CONFTEST)
    testdir.makepyfile(TESTSUITE)

    args = ["--durations=0", "-vv"]
    if plugin_disabled:
        args += ["-p", "no:hypothesispytest"]

    result = testdir.runpytest(*args)
    result.assert_outcomes(passed=2)

    output = "\n".join(result.stdout.lines)
    match = re.search(r"([\d.]+)s call\s+\S+::test_first", output)
    assert match, f"Could not find test_first timing in:\n{output}"
    test_first_time = float(match.group(1))

    if plugin_disabled:
        assert test_first_time >= 0.05, f"took {test_first_time}s, expected >= 0.05s"
    else:
        assert test_first_time < 0.05, f"took {test_first_time}s, expected < 0.05s"
