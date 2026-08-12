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

from hypothesis import (
    HealthCheck,
    Phase,
    given,
    seed,
    settings,
    strategies as st,
    target,
)

common_settings = {
    "database": None,
    "suppress_health_check": list(HealthCheck),
    "phases": [Phase.generate, Phase.target],
}


@pytest.mark.parametrize("seed_val", [0, 1, 2])
def test_finds_threshold_bug_quickly_with_large_budget(seed_val):
    # check that we optimize sooner than halfway for large test case budgets.
    calls = 0
    found_at = None

    @seed(seed_val)
    @settings(max_examples=10_000, **common_settings)
    @given(st.lists(st.integers(0, 1000)))
    def test(ls):
        nonlocal calls, found_at
        calls += 1
        target(min(sum(ls), 50_000))
        if sum(ls) >= 30_000:
            if found_at is None:
                found_at = calls
            raise AssertionError

    with pytest.raises(AssertionError):
        test()
    assert found_at is not None
    assert found_at < 4_000


@pytest.mark.parametrize("seed_val", [0, 1, 2])
def test_reaches_high_scores_with_moderate_budget(seed_val):
    best = 0.0

    @seed(seed_val)
    @settings(max_examples=2000, **common_settings)
    @given(st.lists(st.integers(0, 1000)))
    def test(ls):
        nonlocal best
        score = min(sum(ls), 100_000)
        best = max(best, score)
        target(score)

    test()
    # generous margin to account for unrelated engine changes
    assert best >= 50_000
