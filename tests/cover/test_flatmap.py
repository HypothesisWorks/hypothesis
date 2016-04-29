# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

import pytest

from hypothesis import find, given, assume, settings
from hypothesis.database import ExampleDatabase
from hypothesis.strategies import just, text, lists, floats, tuples, \
    booleans, integers
from hypothesis.internal.compat import Counter

ConstantLists = integers().flatmap(lambda i: lists(just(i)))

OrderedPairs = integers(1, 200).flatmap(
    lambda e: tuples(integers(0, e - 1), just(e))
)

with settings(max_examples=200):
    @given(ConstantLists)
    def test_constant_lists_are_constant(x):
        assume(len(x) >= 3)
        assert len(set(x)) == 1

    @given(OrderedPairs)
    def test_in_order(x):
        assert x[0] < x[1]


def test_flatmap_retrieve_from_db():
    constant_float_lists = floats(0, 1).flatmap(
        lambda x: lists(just(x))
    )

    track = []

    db = ExampleDatabase()

    @given(constant_float_lists)
    @settings(database=db)
    def record_and_test_size(xs):
        if sum(xs) >= 1:
            track.append(xs)
            assert False

    with pytest.raises(AssertionError):
        record_and_test_size()

    assert track
    example = track[-1]
    track = []

    with pytest.raises(AssertionError):
        record_and_test_size()

    assert track[0] == example


def test_flatmap_does_not_reuse_strategies():
    s = lists(max_size=0).flatmap(just)
    assert s.example() is not s.example()


def test_flatmap_has_original_strategy_repr():
    ints = integers()
    ints_up = ints.flatmap(lambda n: integers(min_value=n))
    assert repr(ints) in repr(ints_up)


def test_mixed_list_flatmap():
    s = lists(
        booleans().flatmap(lambda b: booleans() if b else text())
    )

    def criterion(ls):
        c = Counter(type(l) for l in ls)
        return len(c) >= 2 and min(c.values()) >= 3

    result = find(s, criterion)
    assert len(result) == 6
    assert set(result) == set([False, u''])
