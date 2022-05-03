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


TEST_SUITE = """
from hypothesis import given, settings, assume
import hypothesis.strategies as st


first = None

@settings(database=None)
@given(st.integers())
def test_fails_once(some_int):
    assume(abs(some_int) > 1000)
    global first
    if first is None:
        first = some_int

    assert some_int != first
"""


CONTAINS_SEED_INSTRUCTION = re.compile(r"--hypothesis-seed=\d+", re.MULTILINE)


@pytest.mark.parametrize("seed", [0, 42, "foo"])
def test_runs_repeatably_when_seed_is_set(seed, testdir):
    script = testdir.makepyfile(TEST_SUITE)

    results = [
        testdir.runpytest(
            script, "--verbose", "--strict-markers", "--hypothesis-seed", str(seed)
        )
        for _ in range(2)
    ]

    for r in results:
        for l in r.stdout.lines:
            assert "--hypothesis-seed" not in l

    failure_lines = [l for r in results for l in r.stdout.lines if "some_int=" in l]

    assert len(failure_lines) == 2
    assert failure_lines[0] == failure_lines[1]


HEALTH_CHECK_FAILURE = """
import os

from hypothesis import given, strategies as st, assume, reject

RECORD_EXAMPLES = <file>

if os.path.exists(RECORD_EXAMPLES):
    target = None
    with open(RECORD_EXAMPLES, 'r') as i:
        seen = set(map(int, i.read().strip().split("\\n")))
else:
    target = open(RECORD_EXAMPLES, 'w')

@given(st.integers())
def test_failure(i):
    if target is None:
        assume(i not in seen)
    else:
        target.write(f"{i}\\n")
        reject()
"""


def test_repeats_healthcheck_when_following_seed_instruction(testdir, tmpdir):
    health_check_test = HEALTH_CHECK_FAILURE.replace(
        "<file>", repr(str(tmpdir.join("seen")))
    )

    script = testdir.makepyfile(health_check_test)

    initial = testdir.runpytest(script, "--verbose", "--strict-markers")

    initial_output = "\n".join(initial.stdout.lines)

    match = CONTAINS_SEED_INSTRUCTION.search(initial_output)
    assert match is not None

    rerun = testdir.runpytest(script, "--verbose", "--strict-markers", match.group(0))
    rerun_output = "\n".join(rerun.stdout.lines)

    assert "FailedHealthCheck" in rerun_output
    assert "--hypothesis-seed" not in rerun_output

    rerun2 = testdir.runpytest(
        script, "--verbose", "--strict-markers", "--hypothesis-seed=10"
    )
    rerun2_output = "\n".join(rerun2.stdout.lines)
    assert "FailedHealthCheck" not in rerun2_output


SIMPLE_SEEDING_TEST = """
import os

from hypothesis import given, strategies as st

@given(st.integers())
def test_seed(i):
    assert i < 1000
"""


def test_seed_shows_in_verbose_mode(testdir):
    script = testdir.makepyfile(SIMPLE_SEEDING_TEST)
    verbosity_args = "--hypothesis-verbosity=verbose"

    initial = testdir.runpytest(script, verbosity_args, "--strict-markers")

    initial_output = "\n".join(initial.stdout.lines)

    match = CONTAINS_SEED_INSTRUCTION.search(initial_output)
    assert match is not None


def test_seed_is_hidden_when_not_in_verbose_mode(testdir):
    script = testdir.makepyfile(SIMPLE_SEEDING_TEST)
    verbosity_args = "--hypothesis-verbosity=normal"

    initial = testdir.runpytest(script, verbosity_args, "--strict-markers")

    initial_output = "\n".join(initial.stdout.lines)

    match = CONTAINS_SEED_INSTRUCTION.search(initial_output)
    assert match is None
