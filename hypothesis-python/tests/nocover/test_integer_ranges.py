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

from hypothesis import given, settings, strategies as st

from tests.common.utils import Why, xfail_on_crosshair


@xfail_on_crosshair(Why.symbolic_outside_context)
def test_bounded_integers_distribution_of_bit_width_issue_1387_regression():
    values = []

    @settings(database=None, max_examples=1000)
    @given(st.integers(0, 1e100))
    def test(x):
        if 2 <= x <= int(1e100) - 2:  # skip forced-endpoints
            values.append(x)

    test()

    # We draw from a shaped distribution up to 128bit, so we should get some very large
    # but not too many.
    huge = sum(x > 1e25 for x in values)
    assert 1 < huge <= 100


@pytest.mark.parametrize(
    "bounds",
    [
        (-(2**300), 2**500),
        (2**500, 2**501),
        (2**500, 2**500 + 10),
        (2**2000, None),
        (None, -(2**2000)),
        (2**2000, 2**2000 + 100),
    ],
)
def test_integer_bounds(bounds):
    min_value, max_value = bounds

    @given(st.integers(min_value, max_value))
    def f(n):
        if min_value is not None:
            assert min_value <= n
        if max_value is not None:
            assert n <= max_value

    f()


# this test depends on internal HypothesisProvider distribution behavior
@xfail_on_crosshair(Why.other, strict=False)
@pytest.mark.parametrize(
    "min_value, max_value, lower, upper",
    [
        # unbounded: use (-2**128, 2**128).
        (None, None, -(2**128), 2**128),
        # half-bounded at n < 2^127: use (n, 2^128).
        (0, None, 0, 2**128),
        (None, 0, -(2**128), 0),
        (-1000, None, -1000, 2**128),
        (None, 1000, -(2**128), 1000),
        (2**127, None, 2**127, 2**128),
        (None, -(2**127), -(2**128), -(2**127)),
        # half-bounded at n > 2^127: use (n, 2n).
        (2**200, None, 2**200, 2**201),
        (None, -(2**200), -(2**201), -(2**200)),
        (-(2**200), None, -(2**200), 2**201),
        (None, 2**200, -(2**201), 2**200),
    ],
)
def test_integers_unbounded_and_half_bounded(min_value, max_value, lower, upper):
    @given(st.integers(min_value, max_value))
    def f(n):
        assert lower <= n <= upper

    f()
