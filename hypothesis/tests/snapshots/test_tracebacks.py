# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Snapshots of the tracebacks we show when a test fails.

We strip our own frames from tracebacks, so that what you see is the code you
wrote; line numbers are the fragile part of that (see issue #4681).  Most of
these use ``--tb=native``, which unlike pytest's own rendering shows every
frame that survived trimming.
"""

import os
import re
import textwrap
from pathlib import Path

import pytest
from pytest import param

import hypothesis
from hypothesis._settings import _CI_VARS

pytest_plugins = "pytester"

# Where our frames say they come from varies with the install layout: a source
# checkout has `.../src/hypothesis/`, an installed copy `.../site-packages/`.
HYPOTHESIS_ROOT = str(Path(hypothesis.__file__).parent.parent) + os.sep
BANNER = re.compile(r"^=+ .+ =+$")
# The prefix is "  | " or similar for frames nested inside an exception group.
FRAME = re.compile(r'^(?P<prefix>[\s|]*)File "(?P<path>[^"]*)", line \d+, in ')
THIRD_PARTY = re.compile(r"[/\\](?:_pytest|pluggy)[/\\]")
# Which expressions get `~~^~~` anchors under them varies by Python version, and
# the frame above says where we are precisely enough without them.
ANCHORS = re.compile(r"^[\s|]*[~^][~^\s]*$")


def failure_section(lines):
    start = next(i for i, line in enumerate(lines) if " FAILURES " in line) + 1
    end = next(
        (i for i, line in enumerate(lines[start:], start) if BANNER.match(line)),
        len(lines),
    )
    return lines[start:end]


def elide_third_party_frames(lines):
    # Every traceback here is bracketed by pytest and pluggy frames, which say
    # nothing about our trimming.  Collapse each run of them into one line.
    out = []
    dropping = False
    for line in lines:
        if match := FRAME.match(line):
            dropping = bool(THIRD_PARTY.search(match["path"]))
            if not dropping:
                out.append(line)
            elif out[-1:] != [match["prefix"] + "<pytest internals>"]:
                out.append(match["prefix"] + "<pytest internals>")
        elif not dropping:
            out.append(line)
    return out


def normalize(lines, path):
    lines = [
        x
        for x in elide_third_party_frames(failure_section(lines))
        if not ANCHORS.match(x)
    ]
    output = "\n".join(lines)
    output = output.replace(str(path) + os.sep, "").replace(HYPOTHESIS_ROOT, "")
    if os.sep != "/":
        output = output.replace(os.sep, "/")
    output = re.sub(r'("(?:hypothesis/[^"]*|<hypothesis>)", line )\d+', r"\1NN", output)
    output = output.replace("exceptiongroup.ExceptionGroup", "ExceptionGroup")
    output = re.sub(
        r"\d+ valid inputs after [\d.]+ seconds", "N inputs after T", output
    )
    return re.sub(r"^ +x \| .+$", "  x | <timings>", output, flags=re.MULTILINE)


def run(pytester, source, *args):
    pytester.makepyfile(textwrap.dedent(source).strip() + "\n")
    result = pytester.runpytest("--no-header", "-rN", *args)
    result.assert_outcomes(failed=1)
    return normalize(result.stdout.lines, pytester.path)


@pytest.fixture(autouse=True)
def _not_on_ci(monkeypatch):
    # The CI settings profile changes the health-check output we snapshot below.
    for key in _CI_VARS:
        monkeypatch.delenv(key, raising=False)


ERROR_IN_TEST = """
from hypothesis import given, settings, strategies as st

@settings(database=None, derandomize=True, print_blob=False)
@given(st.none())
def test_error_in_test(_):
    1 / 0
"""

# The lambda used to attract the traceback's carets, because we claimed the
# calling frame started at the test's first line.
LAMBDA_IN_TEST = """
from hypothesis import given, settings, strategies as st

@settings(database=None, derandomize=True, print_blob=False)
@given(st.none())
def test_lambda_in_test(_):
    f = lambda: "Hi!"
    1 / 0
"""

ERROR_IN_HELPER = """
from hypothesis import given, settings, strategies as st

def helper(x):
    raise ValueError("boom")

@settings(database=None, derandomize=True, print_blob=False)
@given(st.integers())
def test_error_in_helper(x):
    helper(x)
"""

ERROR_IN_STRATEGY = """
from hypothesis import given, settings, strategies as st

@settings(database=None, derandomize=True, print_blob=False)
@given(st.integers().map(lambda x: 1 / 0))
def test_error_in_strategy(x):
    pass
"""

ERROR_IN_DRAWN_STRATEGY = """
from hypothesis import given, settings, strategies as st

@st.composite
def broken(draw):
    draw(st.integers())
    raise ValueError("boom")

@settings(database=None, derandomize=True, print_blob=False)
@given(st.data())
def test_error_in_drawn_strategy(data):
    data.draw(broken())
"""

MULTIPLE_FAILURES = """
from hypothesis import given, settings, strategies as st

@settings(database=None, derandomize=True, print_blob=False)
@given(st.integers())
def test_multiple_failures(x):
    if x > 100:
        raise ValueError("This number is too big!")
    elif x < -100:
        raise RuntimeError("This number is too small!")
"""

FAILED_HEALTH_CHECK = """
import time
from hypothesis import given, settings, strategies as st

@settings(database=None, derandomize=True, print_blob=False)
@given(st.integers().map(lambda x: time.sleep(0.2)))
def test_failed_health_check(x):
    pass
"""

# @given rejects the missing argument at call time, from a frame of our own.
INVALID_SIGNATURE = """
from hypothesis import given, settings, strategies as st

@settings(database=None, derandomize=True, print_blob=False)
@given(st.none())
def test_invalid_signature():
    pass
"""


@pytest.mark.parametrize(
    "source",
    [
        param(ERROR_IN_TEST, id="error_in_test"),
        param(LAMBDA_IN_TEST, id="lambda_in_test"),
        param(ERROR_IN_HELPER, id="error_in_helper"),
        param(ERROR_IN_STRATEGY, id="error_in_strategy"),
        param(ERROR_IN_DRAWN_STRATEGY, id="error_in_drawn_strategy"),
        param(MULTIPLE_FAILURES, id="multiple_failures"),
        param(FAILED_HEALTH_CHECK, id="failed_health_check"),
        param(INVALID_SIGNATURE, id="invalid_signature"),
    ],
)
def test_traceback_frames(pytester, source, snapshot):
    assert run(pytester, source, "--tb=native") == snapshot


# pytest's own format is what most users see, and the only one in which
# `__tracebackhide__` has any effect - so we cover the cases where it matters.
@pytest.mark.parametrize(
    "source",
    [
        param(ERROR_IN_HELPER, id="error_in_helper"),
        param(INVALID_SIGNATURE, id="invalid_signature"),
        param(MULTIPLE_FAILURES, id="multiple_failures"),
    ],
)
def test_traceback_as_pytest_renders_it(pytester, source, snapshot):
    assert run(pytester, source, "--tb=long") == snapshot
