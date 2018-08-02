# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

from hypothesis.internal.compat import hrange
from hypothesis.internal.conjecture.shrinking.common import Shrinker


"""
This module implements a shrinker for non-negative integers.
"""


class Integer(Shrinker):
    """Attempts to find a smaller sequence satisfying f. Will only perform
    linearly many evaluations, and does not loop to a fixed point.

    Guarantees made at a fixed point:

        1. No individual element may be deleted.
        2. No *adjacent* pair of elements may be deleted.
    """

    def short_circuit(self):
        for i in hrange(3):
            if self.consider(i):
                return True
        return False

    def check_invariants(self, value):
        assert value >= 0

    def left_is_better(self, left, right):
        return left < right

    def run_step(self):
        assert self.current > 2
        self.consider(self.current - 2)
        self.consider(self.current - 1)
        assert self.current > 2
        lo = 2
        while lo + 1 < self.current:
            mid = (lo + self.current) // 2
            if not self.consider(mid):
                lo = mid
