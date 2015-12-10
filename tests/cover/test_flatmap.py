# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

from random import Random

import pytest

from hypothesis import find, given, assume, Settings
from hypothesis.database import ExampleDatabase
from hypothesis.strategies import just, lists, floats, tuples, integers, \
    streaming
from hypothesis.internal.debug import some_template
from hypothesis.internal.compat import hrange
from hypothesis.searchstrategy.narytree import Leaf, n_ary_tree

ConstantLists = integers().flatmap(lambda i: lists(just(i)))

OrderedPairs = integers(1, 200).flatmap(
    lambda e: tuples(integers(0, e - 1), just(e))
)

with Settings(max_examples=200):
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

    @given(constant_float_lists, settings=Settings(database=db))
    def record_and_test_size(xs):
        track.append(xs)
        assert sum(xs) < 1

    with pytest.raises(AssertionError):
        record_and_test_size()

    assert track
    example = track[-1]

    while track:
        track.pop()

    with pytest.raises(AssertionError):
        record_and_test_size()

    assert track[0] == example


def nary_tree_to_strategy(tree):
    if isinstance(tree, Leaf):
        return integers()
    else:
        return tuples(*[
            nary_tree_to_strategy(v) for _, v in tree.keyed_children])


dav_strategy = n_ary_tree(just(None), just(None), just(None)).flatmap(
    nary_tree_to_strategy
)


def test_will_find_a_failure_from_the_database():
    db = ExampleDatabase()

    class Rejected(Exception):
        pass

    @given(
        dav_strategy,
        settings=Settings(max_examples=10, database=db))
    def nope(x):
        raise Rejected()
    try:
        with pytest.raises(Rejected):
            nope()  # pragma: no branch
    finally:
        db.close()


def test_can_still_simplify_if_not_reified():
    strat = ConstantLists
    random = Random(u'test_constant_lists_are_constant')
    template = some_template(strat, random)
    try:
        while True:
            template = next(strat.full_simplify(random, template))
    except StopIteration:
        pass


def test_flatmap_does_not_reuse_strategies():
    s = lists(max_size=0).flatmap(just)
    assert s.example() is not s.example()


def test_flatmap_has_original_strategy_repr():
    ints = integers()
    ints_up = ints.flatmap(lambda n: integers(min_value=n))
    assert repr(ints) in repr(ints_up)


def test_streaming_flatmap_past_point_of_read():
    s = find(
        streaming(integers().flatmap(lambda n: integers(min_value=n))),
        lambda x: x[0])
    assert s[0] == 1
    for i in hrange(100):
        s[i]
