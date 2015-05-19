# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from random import Random

import pytest
from hypothesis import Settings, given, assume, strategy
from hypothesis.database import ExampleDatabase
from hypothesis.strategies import just, lists, floats, tuples, randoms, \
    booleans, integers, complex_numbers
from hypothesis.internal.debug import some_template
from hypothesis.utils.conventions import not_set
from hypothesis.searchstrategy.narytree import Leaf, n_ary_tree

ConstantLists = integers().flatmap(lambda i: lists(just(i)))

OrderedPairs = strategy(integers(1, 200)).flatmap(
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
    constant_float_lists = strategy(floats(0, 1)).flatmap(
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


@given(randoms())
def test_can_recover_from_bad_data_in_mapped_strategy(r):
    param = OrderedPairs.draw_parameter(r)
    template = OrderedPairs.draw_template(r, param)
    OrderedPairs.reify(template)
    assert template.target_data != not_set
    basic = OrderedPairs.to_basic(template)
    assert len(basic) == 4
    assert isinstance(basic, list)
    assert isinstance(basic[-1], list)
    basic[-1] = 1
    new_template = OrderedPairs.from_basic(basic)
    reified = OrderedPairs.reify(new_template)
    assert type(reified) == tuple
    x, y = reified
    assert x < y


def nary_tree_to_strategy(tree):
    if isinstance(tree, Leaf):
        return integers()
    else:
        return tuples(*map(nary_tree_to_strategy, tree.children))


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
        print(x)
        raise Rejected()
    try:
        with pytest.raises(Rejected):
            nope()  # pragma: no branch
    finally:
        db.close()


def test_can_still_simplify_if_not_reified():
    strat = strategy(ConstantLists)
    random = Random('test_constant_lists_are_constant')
    template = some_template(strat, random)
    try:
        while True:
            template = next(strat.full_simplify(random, template))
    except StopIteration:
        pass


def test_flatmap_does_not_reuse_strategies():
    s = lists(max_size=0).flatmap(just)
    assert s.example() is not s.example()


def test_flatmap_can_apply_all_inapplicable_simplifiers():
    random = Random(1)
    s = booleans().flatmap(lambda x: complex_numbers() if x else booleans())
    source_to_total = {}

    while len(source_to_total) < 2:
        t = s.draw_and_produce(random)
        source_to_total[t.source_template] = t
    u = source_to_total[False]
    v = source_to_total[True]
    s.reify(u)
    s.reify(v)

    for p in ((u, v), (v, u)):
        for simplify in s.simplifiers(random, p[0]):
            for target in simplify(random, p[1]):
                assert not s.strictly_simpler(p[1], target)
