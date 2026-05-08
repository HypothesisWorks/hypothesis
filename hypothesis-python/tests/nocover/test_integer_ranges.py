# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import find, given, settings, strategies as st
from hypothesis.strategies import integers

from tests.common.debug import find_any
from tests.common.utils import Why, xfail_on_crosshair


@xfail_on_crosshair(Why.symbolic_outside_context)
def test_bounded_integers_distribution_of_bit_width_issue_1387_regression():
    values = []

    @settings(database=None, max_examples=1000)
    @given(integers(0, 1e100))
    def test(x):
        if 2 <= x <= int(1e100) - 2:  # skip forced-endpoints
            values.append(x)

    test()

    # We draw from a shaped distribution up to 128bit ~7/8 of the time, and
    # uniformly the rest.  So we should get some very large but not too many.
    huge = sum(x > 1e97 for x in values)
    assert huge != 0 or len(values) < 800
    assert huge <= 0.5 * len(values)  # expected ~1/8


@xfail_on_crosshair(Why.symbolic_outside_context)
def test_large_symmetric_bounded_integers_are_symmetric_issue_4624_regression():
    # See https://github.com/HypothesisWorks/hypothesis/issues/4624 - we used to
    # cap large bounded ranges to ``[lower, lower + 2**cap_bits - 1]``, which
    # heavily biased the distribution towards the lower bound.
    values = []

    @settings(database=None, max_examples=2000)
    @given(integers(-(2**63), 2**63))
    def test(x):
        values.append(x)

    test()

    negatives = sum(1 for v in values if v < 0)
    # We expect roughly 50% negative values; allow generous slack for noise.
    # Pre-fix, this was around 80%.
    assert (
        0.3 * len(values) < negatives < 0.7 * len(values)
    ), f"Expected roughly symmetric distribution, got {negatives}/{len(values)} negative"


@xfail_on_crosshair(Why.symbolic_outside_context)
def test_can_find_small_magnitude_in_large_bounded_range_issue_4722_regression():
    # See https://github.com/HypothesisWorks/hypothesis/issues/4722 - small
    # magnitude values should be reachable in large bounded ranges, just as
    # they are in unbounded ranges.
    find(st.integers(-(2**63), 2**63), lambda x: 10 < abs(x) < 10000)


@xfail_on_crosshair(Why.symbolic_outside_context)
def test_large_bounded_range_can_generate_small_values_issue_4722_regression():
    # We should be able to generate values with small absolute magnitude in a
    # very large bounded range.
    find_any(st.integers(-(2**63), 2**63), lambda x: abs(x) < 1000)
