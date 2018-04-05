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

from hypothesis import find, given, settings
from hypothesis.strategies import sets, floats, randoms, integers


@given(randoms())
@settings(max_examples=5, deadline=None)
def test_can_draw_sets_of_hard_to_find_elements(rnd):
    rarebool = floats(0, 1).map(lambda x: x <= 0.01)
    find(
        sets(rarebool, min_size=2), lambda x: True,
        random=rnd, settings=settings(database=None))


@given(sets(integers(), max_size=0))
def test_empty_sets(x):
    assert x == set()


@given(sets(integers(), max_size=2))
def test_bounded_size_sets(x):
    assert len(x) <= 2
