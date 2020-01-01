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

from hypothesis.internal.conjecture.shrinking.common import find_integer

FIND_INTEGER_COSTS = {}


def find_integer_cost(n):
    try:
        return FIND_INTEGER_COSTS[n]
    except KeyError:
        pass

    cost = [0]

    def test(i):
        cost[0] += 1
        return i <= n

    find_integer(test)

    return FIND_INTEGER_COSTS.setdefault(n, cost[0])
