# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

from random import Random

from hypothesis.types import RandomWithSeed
from hypothesis.strategies import lists, one_of, booleans


def test_can_apply_simplifiers_to_other_types():
    r = Random(0)
    s = one_of(booleans(), lists(booleans()))
    template1 = s.draw_and_produce(r)
    while True:
        template2 = s.draw_and_produce(r)
        if template2[0] != template1[0]:
            break
    for simplify in s.simplifiers(r, template1):
        assert list(simplify(r, template2)) == []


def test_can_draw_from_a_random_with_seed():
    r = RandomWithSeed(0)
    s = one_of(booleans(), lists(booleans()))
    s.draw_and_produce(r)
