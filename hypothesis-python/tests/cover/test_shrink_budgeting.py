# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys

import pytest

from hypothesis.internal.conjecture.shrinking import Integer, Ordering


@pytest.mark.parametrize(
    "Shrinker, value",
    [
        (Integer, 2**16),
        (Integer, int(sys.float_info.max)),
        (Ordering, [[100] * 10]),
        (Ordering, [i * 100 for i in (range(5))]),
        (Ordering, [i * 100 for i in reversed(range(5))]),
    ],
)
def test_meets_budgetary_requirements(Shrinker, value):
    shrinker = Shrinker(value, lambda x: x == value)
    shrinker.run()
    assert shrinker.calls <= 10
