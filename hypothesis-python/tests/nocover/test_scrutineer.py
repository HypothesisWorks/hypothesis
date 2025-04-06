# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import json
import sys
import sysconfig

import pytest

from hypothesis import given, note, settings, strategies as st
from hypothesis.internal.compat import PYPY
from hypothesis.internal.scrutineer import make_report
from hypothesis.vendor import pretty

# We skip tracing for explanations under PyPy, where it has a large performance
# impact, or if there is already a trace function (e.g. coverage or a debugger)
pytestmark = pytest.mark.skipif(PYPY or sys.gettrace(), reason="See comment")

BUG_MARKER = "# BUG"
DEADLINE_PRELUDE = """
from datetime import timedelta
from hypothesis.errors import DeadlineExceeded
"""
PRELUDE = """
from hypothesis import Phase, given, settings, strategies as st

@settings(phases=tuple(Phase), derandomize=True)
"""
TRIVIAL = """
@given(st.integers())
def test_reports_branch_in_test(x):
    if x > 10:
        raise AssertionError  # BUG
"""
MULTIPLE_BUGS = """
@given(st.integers(), st.integers())
def test_reports_branch_in_test(x, y):
    if x > 10:
        raise (AssertionError if x % 2 else Exception)  # BUG
"""
FRAGMENTS = (
    pytest.param(TRIVIAL, id="trivial"),
    pytest.param(MULTIPLE_BUGS, id="multiple-bugs"),
)


def get_reports(file_contents, *, testdir):
    # Takes the source code string with "# BUG" comments, and returns a list of
    # multi-line report strings which we expect to see in explain-mode output.
    # The list length is the number of explainable bugs, usually one.
    test_file = str(testdir.makepyfile(file_contents))
    pytest_stdout = str(testdir.runpytest_inprocess(test_file, "--tb=native").stdout)

    crash = "AttributeError: module 'blib2to3.pygram' has no attribute 'python_symbols'"
    if crash in pytest_stdout:
        pytest.xfail(reason="upstream error in Black")

    explanations = {
        i: {(test_file, i)}
        for i, line in enumerate(file_contents.splitlines())
        if line.endswith(BUG_MARKER)
    }
    expected = [
        ("\n".join(r), "\n    | ".join(r))  # single, ExceptionGroup
        for r in make_report(explanations).values()
    ]
    return pytest_stdout, expected


@pytest.mark.parametrize("code", FRAGMENTS)
def test_explanations(code, testdir):
    pytest_stdout, expected = get_reports(PRELUDE + code, testdir=testdir)
    assert len(expected) == code.count(BUG_MARKER)
    for single, group in expected:
        assert single in pytest_stdout or group in pytest_stdout


@pytest.mark.parametrize("code", FRAGMENTS)
def test_no_explanations_if_deadline_exceeded(code, testdir):
    code = code.replace("AssertionError", "DeadlineExceeded(timedelta(), timedelta())")
    pytest_stdout, _ = get_reports(DEADLINE_PRELUDE + PRELUDE + code, testdir=testdir)
    assert "Explanation:" not in pytest_stdout


NO_SHOW_CONTEXTLIB = """
from contextlib import contextmanager
from hypothesis import given, strategies as st, Phase, settings

@contextmanager
def ctx():
    yield

@settings(phases=list(Phase))
@given(st.integers())
def test(x):
    with ctx():
        assert x < 100
"""


@pytest.mark.skipif(PYPY, reason="Tracing is slow under PyPy")
def test_skips_uninformative_locations(testdir):
    pytest_stdout, _ = get_reports(NO_SHOW_CONTEXTLIB, testdir=testdir)
    assert "Explanation:" not in pytest_stdout


@given(st.randoms())
@settings(max_examples=5)
def test_report_sort(random):
    # show local files first, then site-packages, then stdlib

    lines = [
        # local
        (__file__, 10),
        # site-packages
        (pytest.__file__, 123),
        (pytest.__file__, 124),
        # stdlib
        (json.__file__, 43),
        (json.__file__, 42),
    ]
    random.shuffle(lines)
    explanations = {"origin": lines}
    report = make_report(explanations)
    report_lines = report["origin"][2:]
    report_lines = [line.strip() for line in report_lines]

    expected_lines = [
        f"{__file__}:10",
        f"{pytest.__file__}:123",
        f"{pytest.__file__}:124",
        f"{json.__file__}:42",
        f"{json.__file__}:43",
    ]

    note(f"sysconfig.get_paths(): {pretty.pretty(sysconfig.get_paths())}")
    note(f"actual lines: {pretty.pretty(report_lines)}")
    note(f"expected lines: {pretty.pretty(expected_lines)}")

    assert report_lines == expected_lines
