# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import Phase, given, seed, settings, strategies as st, target

pytest_plugins = "pytester"

TESTSUITE = """
from hypothesis import given, strategies as st, target

@given(st.integers(min_value=0))
def test_threshold_problem(x):
    target(float(x))
    {0}target(float(x * 2), label="double")
    {0}assert x <= 100000
    assert x <= 100
"""


@pytest.mark.parametrize("multiple", [False, True])
def test_reports_target_results(testdir, multiple):
    script = testdir.makepyfile(TESTSUITE.format("" if multiple else "# "))
    result = testdir.runpytest(script, "--tb=native", "-rN")
    out = "\n".join(result.stdout.lines)
    assert "Falsifying example" in out
    assert "x=101" in out, out
    assert out.count("Highest target score") == 1
    assert result.ret != 0


def test_targeting_increases_max_length():
    strat = st.lists(st.booleans())

    @settings(database=None, max_examples=200, phases=[Phase.generate, Phase.target])
    @given(strat)
    def test_with_targeting(ls):
        target(float(len(ls)))
        assert len(ls) <= 80

    with pytest.raises(AssertionError):
        test_with_targeting()


@given(st.integers(), st.integers())
def test_target_returns_value(a, b):
    difference = target(abs(a - b))
    assert difference == abs(a - b)
    assert isinstance(difference, int)


def test_targeting_can_be_disabled():
    strat = st.lists(st.integers(0, 255))

    def score(enabled):
        result = 0
        phases = [Phase.generate]
        if enabled:
            phases.append(Phase.target)

        @seed(0)
        @settings(database=None, max_examples=100, phases=phases)
        @given(strat)
        def test(ls):
            nonlocal result
            # cap the score to avoid long test times by unbounded driving of list
            # length upwards
            score = min(sum(ls), 10_000)
            result = max(result, score)
            target(score)

        test()
        return result

    assert score(enabled=True) > score(enabled=False)


def test_issue_2395_regression():
    @given(d=st.floats().filter(lambda x: abs(x) < 1000))
    @settings(max_examples=1000, database=None)
    @seed(93962505385993024185959759429298090872)
    def test_targeting_square_loss(d):
        target(-((d - 42.5) ** 2.0))

    test_targeting_square_loss()
