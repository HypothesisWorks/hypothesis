# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Snapshot tests investigating impersonation traceback issues.

These tests capture the full pytest output for various scenarios where
hypothesis's function impersonation (co_filename/co_firstlineno replacement)
affects tracebacks. See https://github.com/HypothesisWorks/hypothesis/issues/4681
"""

import re
import textwrap


from hypothesis._settings import _CI_VARS

pytest_plugins = "pytester"


def normalize_output(output, test_filename, test_source_lines):
    """Normalize unstable parts of pytest output for snapshot comparison.

    Line numbers from the test file are replaced with the actual source line
    content, making the snapshots self-documenting about what the traceback is
    pointing at. Line numbers from other files are replaced with NN.
    """

    def replace_lineno(m):
        filename = m.group(1)
        lineno_str = m.group(2)
        trailing = m.group(3) or ""
        if filename.endswith(test_filename):
            lineno = int(lineno_str)
            if 1 <= lineno <= len(test_source_lines):
                line_content = test_source_lines[lineno - 1].strip()
            else:
                line_content = f"<line {lineno} out of range>"
            return f"{filename}: # {line_content}{trailing}"
        return f"{filename}:NN:{trailing}"

    output = re.sub(
        r"([\w./\\-]+\.py):(\d+):(\s.*)?$",
        replace_lineno,
        output,
        flags=re.MULTILINE,
    )
    output = re.sub(r", line \d+,", ", line NN,", output)
    # Normalize seeds
    output = re.sub(r"@seed\(\d+\)", "@seed(0)", output)
    output = re.sub(r"--hypothesis-seed=\d+", "--hypothesis-seed=0", output)
    # Normalize patch file paths
    output = re.sub(
        r"`git apply .hypothesis/patches/[^`]+`",
        "`git apply .hypothesis/patches/PATCH`",
        output,
    )
    # Normalize timing in healthcheck output
    output = re.sub(
        r"only generated \d+ valid inputs after [\d.]+ seconds",
        "only generated N valid inputs after T seconds",
        output,
    )
    output = re.sub(
        r"(count \| fraction \|    slowest draws \(seconds\))\n.*",
        r"\1\n  x | <timing data>",
        output,
    )
    # Normalize test session timing
    output = re.sub(r"in [\d.]+s =", "in T =", output)
    return output


def get_failure_output(testdir, test_code, *extra_args):
    """Run a test file via pytester and return normalized failure output."""
    source = textwrap.dedent(test_code).strip()
    source_lines = source.splitlines()
    script = testdir.makepyfile(source)
    result = testdir.runpytest(script, "--tb=long", "--no-header", "-rN", *extra_args)
    raw = "\n".join(result.stdout.lines)
    return normalize_output(raw, script.basename, source_lines)


# ---- Issue #4681 Example 1: Basic ZeroDivisionError ----
# The impersonation causes an intermediate frame to appear pointing at the
# user's function definition line rather than actual hypothesis internals.

ISSUE_EXAMPLE_BASIC = """
from hypothesis import given, settings
import hypothesis.strategies as st

@settings(database=None, derandomize=True)
@given(st.none())
def test_basic_traceback(_):
    1/0
"""


def test_issue_basic_traceback(testdir, snapshot):
    assert get_failure_output(testdir, ISSUE_EXAMPLE_BASIC) == snapshot


# ---- Issue #4681 Example 2: Lambda false positive ----
# When an impersonated function contains a lambda, the carets in the traceback
# erroneously point to content inside the lambda.

ISSUE_EXAMPLE_LAMBDA = """
from hypothesis import given, settings
import hypothesis.strategies as st

@settings(database=None, derandomize=True)
@given(st.none())
def test_lambda_traceback(_):
    f = lambda: \"\"\"Hi!\"\"\"
    1/0
"""


def test_issue_lambda_traceback(testdir, snapshot):
    assert get_failure_output(testdir, ISSUE_EXAMPLE_LAMBDA) == snapshot


# ---- Issue #4681 Example 3: Wrong function name ----
# When a user forgets a parameter in their test signature, the traceback claims
# code was executed inside `wrapped_test` at a line in the user's file.

ISSUE_EXAMPLE_WRONG_FUNCTION = """
from hypothesis import given, settings
import hypothesis.strategies as st

@settings(database=None, derandomize=True)
@given(st.none())
def test_wrong_function():
    1/0
"""


def test_issue_wrong_function_traceback(testdir, snapshot):
    assert get_failure_output(testdir, ISSUE_EXAMPLE_WRONG_FUNCTION) == snapshot


# ---- Healthcheck traceback hiding ----
# This is the test from test_capture.py that verifies hypothesis internals
# are hidden from the traceback when a HealthCheck fails.

HEALTHCHECK_TRACEBACK = """
from hypothesis import given, settings
from hypothesis.strategies import integers
import time
@given(integers().map(lambda x: time.sleep(0.2)))
def test_healthcheck_traceback_is_hidden(x):
    pass
"""


def test_healthcheck_traceback(testdir, monkeypatch, snapshot):
    for key in _CI_VARS:
        monkeypatch.delenv(key, raising=False)
    assert get_failure_output(testdir, HEALTHCHECK_TRACEBACK) == snapshot


# ---- Successful test (baseline) ----
# A simple passing test to confirm no extraneous traceback output.

SIMPLE_PASSING = """
from hypothesis import given, settings
import hypothesis.strategies as st

@settings(database=None, derandomize=True)
@given(st.none())
def test_simple_passing(_):
    pass
"""


def test_simple_passing(testdir, snapshot):
    assert get_failure_output(testdir, SIMPLE_PASSING) == snapshot


# ---- Multiple frames in traceback ----
# Test that exercises a deeper call stack to see how impersonation
# affects the intermediate frames.

DEEP_TRACEBACK = """
from hypothesis import given, settings
import hypothesis.strategies as st

def helper(x):
    raise ValueError("boom")

@settings(database=None, derandomize=True)
@given(st.integers())
def test_deep_traceback(x):
    helper(x)
"""


def test_deep_traceback(testdir, snapshot):
    assert get_failure_output(testdir, DEEP_TRACEBACK) == snapshot


# ---- Map with traceback ----
# Test that exercises a .map() call that fails, to see how the
# impersonation affects the traceback through map internals.

MAP_FAILURE = """
from hypothesis import given, settings
import hypothesis.strategies as st

@settings(database=None, derandomize=True)
@given(st.integers().map(lambda x: 1/0))
def test_map_failure(x):
    pass
"""


def test_map_failure_traceback(testdir, snapshot):
    assert get_failure_output(testdir, MAP_FAILURE) == snapshot
