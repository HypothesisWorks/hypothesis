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

BUG_MARKER = "# BUG"
PRELUDE = """
from hypothesis import Phase, given, settings, strategies as st

@settings(phases=tuple(Phase), derandomize=True)
"""


def expected_reports(file_contents, fname):
    # Takes the source code string with "# BUG" comments, and returns a list of
    # multi-line report strings which we expect to see in explain-mode output.
    # The list length is the number of explainable bugs, usually one.
    explanations = {
        i: {(fname, i)}
        for i, line in enumerate(file_contents.splitlines())
        if line.endswith(BUG_MARKER)
    }
    return ["\n".join(r) for k, r in make_report(explanations).items()]


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


# We skip tracing for explanations under PyPy, where it has a large performance
# impact, or if there is already a trace function (e.g. coverage or a debugger)
@pytest.mark.skipif(PYPY or sys.gettrace(), reason="See comment")
@pytest.mark.parametrize(
    "code",
    [
        pytest.param(TRIVIAL, id="trivial"),
        pytest.param(MULTIPLE_BUGS, id="multiple-bugs"),
    ],
)
def test_explanations(code, testdir):
    code = PRELUDE + code
    test_file = str(testdir.makepyfile(code))
    pytest_stdout = str(testdir.runpytest_inprocess(test_file, "--tb=native").stdout)
    expected = expected_reports(code, fname=test_file)
    assert len(expected) == code.count(BUG_MARKER)
    for report in expected:
        assert report in pytest_stdout
