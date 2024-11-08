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

from hypothesis.internal.compat import WINDOWS, escape_unicode_characters

pytest_plugins = "pytester"

TESTSUITE = """
from hypothesis import given, settings, Verbosity
from hypothesis.strategies import integers

@settings(verbosity=Verbosity.verbose)
@given(integers())
def test_should_be_verbose(x):
    pass

"""


@pytest.mark.parametrize("capture,expected", [("no", True), ("fd", False)])
def test_output_without_capture(testdir, capture, expected):
    script = testdir.makepyfile(TESTSUITE)
    result = testdir.runpytest(script, "--verbose", "--capture", capture)
    out = "\n".join(result.stdout.lines)
    assert "test_should_be_verbose" in out
    assert ("Trying example" in out) == expected
    assert result.ret == 0


UNICODE_EMITTING = """
import pytest
from hypothesis import given, settings, Verbosity
from hypothesis.strategies import text
import sys

def test_emits_unicode():
    @settings(verbosity=Verbosity.verbose)
    @given(text())
    def test_should_emit_unicode(t):
        assert all(ord(c) <= 1000 for c in t), ascii(t)
    with pytest.raises(AssertionError):
        test_should_emit_unicode()
"""


@pytest.mark.xfail(
    WINDOWS,
    reason="Encoding issues in running the subprocess, possibly pytest's fault",
    strict=False,  # It's possible, if rare, for this to pass on Windows too.
)
def test_output_emitting_unicode(testdir, monkeypatch):
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("LANG", "C")
    script = testdir.makepyfile(UNICODE_EMITTING)
    result = getattr(testdir, "runpytest_subprocess", testdir.runpytest)(
        script, "--verbose", "--capture=no"
    )
    out = "\n".join(result.stdout.lines)
    assert "test_emits_unicode" in out
    assert chr(1001) in out or escape_unicode_characters(chr(1001)) in out
    assert result.ret == 0


def get_line_num(token, result, skip_n=0):
    skipped = 0
    for i, line in enumerate(result.stdout.lines):
        if token in line:
            if skip_n == skipped:
                return i
            else:
                skipped += 1
    raise AssertionError(
        f"Token {token!r} not found (skipped {skipped} of planned {skip_n} skips)"
    )


TRACEBACKHIDE_HEALTHCHECK = """
from hypothesis import given, settings
from hypothesis.strategies import integers
import time
@given(integers().map(lambda x: time.sleep(0.2)))
def test_healthcheck_traceback_is_hidden(x):
    pass
"""


def test_healthcheck_traceback_is_hidden(testdir, monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    script = testdir.makepyfile(TRACEBACKHIDE_HEALTHCHECK)
    result = testdir.runpytest(script, "--verbose")
    def_token = "__ test_healthcheck_traceback_is_hidden __"
    timeout_token = ": FailedHealthCheck"
    def_line = get_line_num(def_token, result)
    timeout_line = get_line_num(timeout_token, result)
    assert timeout_line - def_line == 9


COMPOSITE_IS_NOT_A_TEST = """
from hypothesis.strategies import composite, none
@composite
def test_data_factory(draw):
    return draw(none())
"""


def test_deprecation_of_strategies_as_tests(testdir):
    script = testdir.makepyfile(COMPOSITE_IS_NOT_A_TEST)
    testdir.runpytest(script).assert_outcomes(failed=1)
