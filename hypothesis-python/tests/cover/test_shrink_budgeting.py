# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math
import sys

import pytest

from hypothesis.internal.conjecture.shrinking import Integer, Lexical, Ordering


def measure_baseline(cls, value, **kwargs):
    shrinker = cls(value, lambda x: x == value, **kwargs)
    shrinker.run()
    return shrinker.calls


@pytest.mark.parametrize("cls", [Lexical, Ordering])
@pytest.mark.parametrize("example", [[255] * 8])
def test_meets_budgetary_requirements(cls, example):
    # Somewhat arbitrary but not unreasonable budget.
    n = len(example)
    budget = n * math.ceil(math.log(n, 2)) + 5
    assert measure_baseline(cls, example) <= budget


def test_integer_shrinking_is_parsimonious():
    assert measure_baseline(Integer, int(sys.float_info.max)) <= 10
