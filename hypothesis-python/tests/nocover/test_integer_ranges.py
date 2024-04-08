# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given, settings
from hypothesis.strategies import integers


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
