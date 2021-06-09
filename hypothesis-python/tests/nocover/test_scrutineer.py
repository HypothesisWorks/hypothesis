# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

import sys

import pytest

from hypothesis.internal.compat import PYPY
from hypothesis.internal.scrutineer import make_report

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

    explanations = {
        i: {(test_file, i)}
        for i, line in enumerate(file_contents.splitlines())
        if line.endswith(BUG_MARKER)
    }
    expected = ["\n".join(r) for k, r in make_report(explanations).items()]
    return pytest_stdout, expected


@pytest.mark.parametrize("code", FRAGMENTS)
def test_explanations(code, testdir):
    pytest_stdout, expected = get_reports(PRELUDE + code, testdir=testdir)
    assert len(expected) == code.count(BUG_MARKER)
    for report in expected:
        assert report in pytest_stdout


@pytest.mark.parametrize("code", FRAGMENTS)
def test_no_explanations_if_deadline_exceeded(code, testdir):
    code = code.replace("AssertionError", "DeadlineExceeded(timedelta(), timedelta())")
    pytest_stdout, _ = get_reports(DEADLINE_PRELUDE + PRELUDE + code, testdir=testdir)
    assert "Explanation:" not in pytest_stdout
