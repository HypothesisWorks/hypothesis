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

import re
import sys

import pytest

from hypothesis.internal.compat import PYPY
from hypothesis.internal.scrutineer import HAD_TRACE

CODE_SAMPLE = """
from hypothesis import Phase, given, settings, strategies as st

@settings(phases=tuple(Phase), derandomize=True)
@given(st.integers())
def test_reports_branch_in_test(x):
    if x > 10:
        raise AssertionError  # BUG
"""


@pytest.mark.skipif(PYPY, reason="Tracing is slow under PyPy")
def test_cannot_explain_message(testdir):
    # Most of the explanation-related code can't be run under coverage, but
    # what we can cover is the code that prints a message when the explanation
    # tracer couldn't be installed.

    no_tracer = sys.gettrace() is None
    try:
        if no_tracer:
            sys.settrace(lambda frame, event, arg: None)
        test_file = testdir.makepyfile(CODE_SAMPLE)
        testdir.runpytest_inprocess(test_file, "--tb=native").stdout.re_match_lines(
            [r"Explanation:", re.escape(HAD_TRACE)], consecutive=True
        )
    finally:
        if no_tracer:
            sys.settrace(None)
