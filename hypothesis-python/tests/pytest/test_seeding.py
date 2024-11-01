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
            script, "--verbose", "--strict-markers", f"--hypothesis-seed={seed}", "-rN"
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
    with open(RECORD_EXAMPLES, "r", encoding="utf-8") as i:
        seen = set(map(int, i.read().strip().split("\\n")))
else:
    target = open(RECORD_EXAMPLES, "w", encoding="utf-8")

@given(st.integers())
def test_failure(i):
    if target is None:
        assume(i not in seen)
    else:
        target.write(f"{i}\\n")
        reject()
"""


def test_repeats_healthcheck_when_following_seed_instruction(
    testdir, tmp_path, monkeypatch
):
    monkeypatch.delenv("CI", raising=False)
    health_check_test = HEALTH_CHECK_FAILURE.replace(
        "<file>", repr(str(tmp_path / "seen"))
    )

    script = testdir.makepyfile(health_check_test)

    initial = testdir.runpytest(script, "--verbose", "--strict-markers")

    match = CONTAINS_SEED_INSTRUCTION.search("\n".join(initial.stdout.lines))
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
