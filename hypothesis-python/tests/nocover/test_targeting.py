# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import pytest

from hypothesis import Phase, given, settings, strategies as st, target

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
    result = testdir.runpytest(script)
    out = "\n".join(result.stdout.lines)
    assert "Falsifying example" in out
    assert "x=101" in out
    assert out.count("Highest target score") == 1
    assert out.index("Highest target score") < out.index("Falsifying example")
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
