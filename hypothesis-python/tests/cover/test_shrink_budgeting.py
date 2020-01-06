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

import math
import sys
from random import Random

import pytest

from hypothesis.internal.conjecture.shrinking import Integer, Lexical, Ordering


def measure_baseline(cls, value, **kwargs):
    shrinker = cls(value, lambda x: x == value, random=Random(0), **kwargs)
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
