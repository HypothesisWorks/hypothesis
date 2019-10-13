# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import re

import pytest

from hypothesis.internal.compat import hrange

pytest_plugins = str("pytester")


TEST_SUITE = """
from hypothesis import given, settings, assume
import hypothesis.strategies as st


first = None

@settings(database=None)
@given(st.integers())
def test_fails_once(some_int):
    assume(abs(some_int) > 10000)
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
            script, "--verbose", "--strict", "--hypothesis-seed", str(seed)
        )
        for _ in hrange(2)
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
        target.write("%s\\n" % (i,))
        reject()
"""


def test_repeats_healthcheck_when_following_seed_instruction(testdir, tmpdir):
    health_check_test = HEALTH_CHECK_FAILURE.replace(
        "<file>", repr(str(tmpdir.join("seen")))
    )

    script = testdir.makepyfile(health_check_test)

    initial = testdir.runpytest(script, "--verbose", "--strict")

    match = CONTAINS_SEED_INSTRUCTION.search("\n".join(initial.stdout.lines))
    initial_output = "\n".join(initial.stdout.lines)

    match = CONTAINS_SEED_INSTRUCTION.search(initial_output)
    assert match is not None

    rerun = testdir.runpytest(script, "--verbose", "--strict", match.group(0))
    rerun_output = "\n".join(rerun.stdout.lines)

    assert "FailedHealthCheck" in rerun_output
    assert "--hypothesis-seed" not in rerun_output

    rerun2 = testdir.runpytest(script, "--verbose", "--strict", "--hypothesis-seed=10")
    rerun2_output = "\n".join(rerun2.stdout.lines)
    assert "FailedHealthCheck" not in rerun2_output


BAD_USE_OF_SEED = """
import random
import pytest
from hypothesis import given
from hypothesis.strategies import integers

@pytest.fixture(autouse=True)
def fix():
    random.seed(1337)

@given(integers())
def test_foo(x):
    pass

@given(integers())
def test_bar(x):
    pass
"""


def test_detects_tests_seeding(testdir):
    # Checks that our detection actually works
    script = testdir.makepyfile(BAD_USE_OF_SEED)
    testdir.runpytest(script, "-Werror").assert_outcomes(passed=1, failed=1)


RANDOM_MODULE_STRATEGY_REGRESSION = """
import random
from hypothesis import given
from hypothesis.strategies import random_module

@given(random_module())
def test_foo(x):
    pass

@given(random_module())
def test_bar(x):
    pass
"""


def test_detects_polluted_global_random_state(testdir):
    # Regression test for https://github.com/HypothesisWorks/hypothesis/issues/1918
    script = testdir.makepyfile(RANDOM_MODULE_STRATEGY_REGRESSION)
    testdir.runpytest(script, "-Werror").assert_outcomes(passed=2, failed=0)
