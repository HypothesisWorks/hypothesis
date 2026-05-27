# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis.internal.conjecture.shrinking.common import find_integer

FIND_INTEGER_COSTS = {}


def find_integer_cost(n):
    try:
        return FIND_INTEGER_COSTS[n]
    except KeyError:
        pass

    cost = 0

    def test(i):
        nonlocal cost
        cost += 1
        return i <= n

    find_integer(test)

    return FIND_INTEGER_COSTS.setdefault(n, cost)
