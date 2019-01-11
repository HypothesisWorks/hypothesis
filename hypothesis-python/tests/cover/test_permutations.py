# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

from hypothesis import given
from hypothesis.strategies import data, integers, permutations, sets
from tests.common.debug import minimal
from tests.common.utils import checks_deprecated_behaviour


def test_can_find_non_trivial_permutation():
    x = minimal(permutations(list(range(5))), lambda x: x[0] != 0)

    assert x == [1, 0, 2, 3, 4]


@given(permutations(list(u"abcd")))
def test_permutation_values_are_permutations(perm):
    assert len(perm) == 4
    assert set(perm) == set(u"abcd")


@given(permutations([]))
def test_empty_permutations_are_empty(xs):
    assert xs == []


@checks_deprecated_behaviour
@given(data=data(), xs=sets(integers()))
def test_non_sequence_types_are_deprecated(data, xs):
    p = data.draw(permutations(xs))
    assert xs == set(p)
