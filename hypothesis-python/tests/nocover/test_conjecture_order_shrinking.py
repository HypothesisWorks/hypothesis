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

from random import Random

import hypothesis.strategies as st
from hypothesis import given, example
from hypothesis.internal.conjecture.shrinking import Ordering


@example([0, 1, -1])
@given(st.lists(st.integers()))
def test_shrinks_down_to_sorted_the_slow_way(ls):
    # We normally would short-circuit and find that we can sort this
    # automatically, but here we test that a single run_step could put the
    # list in sorted order anyway if it had to, and that that is just an
    # optimisation.
    shrinker = Ordering(ls, lambda ls: True, random=Random(0), full=False)
    shrinker.run_step()
    assert list(shrinker.current) == sorted(ls)
