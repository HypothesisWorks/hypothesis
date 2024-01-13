# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from pathlib import Path


pytest_plugins = "pytester"

TEST_SCRIPT = """
def test_noop():
    pass
"""

SIDEEFFECT_SCRIPT = """
import hypothesis.strategies as st

st.from_regex(".").is_empty
"""


def test_conftest_sideeffect_warning(testdir):
    testdir.makeconftest(SIDEEFFECT_SCRIPT)
    script = testdir.makepyfile(TEST_SCRIPT)
    result = testdir.runpytest_subprocess(script)
    result.assert_outcomes(passed=1)
    assert "HypothesisSideeffectWarning" in "\n".join(result.errlines)


def test_conftest_sideeffect_pinpoint_error(testdir, monkeypatch):
    monkeypatch.setenv("PYTHONWARNINGS", "error")
    monkeypatch.setenv("HYPOTHESIS_WARN_SIDEEFFECT", "1")
    testdir.makeconftest(SIDEEFFECT_SCRIPT)
    script = testdir.makepyfile(TEST_SCRIPT)
    result = testdir.runpytest_subprocess(script)
    assert "st.from_regex" in "\n".join(result.errlines)


def test_plugin_sideeffect_warning(testdir):
    testdir.makepyfile(sideeffect_plugin=SIDEEFFECT_SCRIPT)
    script = testdir.makepyfile(TEST_SCRIPT)
    result = testdir.runpytest_subprocess(script, "-p", "sideeffect_plugin")
    result.assert_outcomes(passed=1)
    assert "HypothesisSideeffectWarning" in "\n".join(result.errlines)


def test_plugin_sideeffect_pinpoint_error(testdir, monkeypatch):
    monkeypatch.setenv("PYTHONWARNINGS", "error")
    monkeypatch.setenv("HYPOTHESIS_WARN_SIDEEFFECT", "1")
    testdir.makepyfile(sideeffect_plugin=SIDEEFFECT_SCRIPT)
    script = testdir.makepyfile(TEST_SCRIPT)
    result = testdir.runpytest_subprocess(script, "-p", "sideeffect_plugin")
    assert "st.from_regex" in "\n".join(result.errlines)
