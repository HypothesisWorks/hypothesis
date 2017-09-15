# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import re

import pytest

from hypothesis.internal.compat import hrange

pytest_plugins = str('pytester')


TEST_SUITE = """
from hypothesis import given, settings
import hypothesis.strategies as st


first = None

@settings(database=None)
@given(st.text(min_size=3))
def test_fails_once(some_string):
    global first
    if first is None:
        first = some_string

    assert some_string != first
"""


CONTAINS_SEED_INSTRUCTION = re.compile(r"--hypothesis-seed=\d+", re.MULTILINE)


@pytest.mark.parametrize('seed', [0, 42, 'foo'])
def test_runs_repeatably_when_seed_is_set(seed, testdir):
    script = testdir.makepyfile(TEST_SUITE)

    results = [
        testdir.runpytest(
            script, '--verbose', '--strict', '--hypothesis-seed', str(seed)
        )
        for _ in hrange(2)
    ]

    for r in results:
        for l in r.stdout.lines:
            assert '--hypothesis-seed' not in l

    failure_lines = [
        l
        for r in results
        for l in r.stdout.lines
        if 'some_string=' in l
    ]

    assert len(failure_lines) == 2
    assert failure_lines[0] == failure_lines[1]


def test_runs_repeatably_when_following_seed_instruction(testdir):
    script = testdir.makepyfile(TEST_SUITE)
    initial = testdir.runpytest(script, '--verbose', '--strict',)

    match = CONTAINS_SEED_INSTRUCTION.search('\n'.join(initial.stdout.lines))
    assert match is not None

    rerun = testdir.runpytest(script, '--verbose', '--strict', match.group(0))

    for l in rerun.stdout.lines:
        assert '--hypothesis-seed' not in l

    results = [initial, rerun]

    failure_lines = [
        l
        for r in results
        for l in r.stdout.lines
        if 'some_string=' in l
    ]

    assert len(failure_lines) == 2
    assert failure_lines[0] == failure_lines[1]
