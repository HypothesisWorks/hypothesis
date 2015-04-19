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
from collections import namedtuple

import pytest
from hypothesis import Settings, given, assume, strategy
from hypothesis.database import ExampleDatabase
from hypothesis.specifiers import just, one_of, sampled_from, \
    floats_in_range, integers_in_range
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.searchstrategy.narytree import Leaf, NAryTree
from hypothesis.searchstrategy.strategies import BuildContext, \
    MappedSearchStrategy

ConstantLists = strategy(int).flatmap(lambda i: [just(i)])

OrderedPairs = strategy(integers_in_range(1, 200)).flatmap(
    lambda e: (integers_in_range(0, e - 1), just(e))
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
    constant_float_lists = strategy(floats_in_range(0, 1)).flatmap(
        lambda x: [just(x)]
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


@given(Random)
def test_can_recover_from_bad_data_in_mapped_strategy(r):
    param = OrderedPairs.draw_parameter(r)
    template = OrderedPairs.draw_template(BuildContext(r), param)
    OrderedPairs.reify(template)
    for simplification in OrderedPairs.full_simplify(r, template):
        if isinstance(simplification, OrderedPairs.TemplateFromTemplate):
            break
    else:
        assume(False)
    assume(isinstance(simplification, OrderedPairs.TemplateFromTemplate))
    basic = OrderedPairs.to_basic(simplification)
    assert len(basic) == 4
    assert isinstance(basic, list)
    assert isinstance(basic[-1], list)
    basic[-1] = 1
    new_template = OrderedPairs.from_basic(basic)
    assert isinstance(new_template, OrderedPairs.TemplateFromBasic)
    reified = OrderedPairs.reify(new_template)
    assert type(reified) == tuple
    x, y = reified
    assert x < y


class Foo(object):
    pass


def nary_tree_to_descriptor(tree):
    if isinstance(tree, Leaf):
        return int
    else:
        return tuple(map(nary_tree_to_descriptor, tree.children))


@strategy.extend_static(Foo)
def dav_strategy(cls, settings):
    return strategy(NAryTree(int, int, int), settings).flatmap(
        nary_tree_to_descriptor
    )


def test_will_find_a_failure_from_the_database():
    db = ExampleDatabase()

    class Rejected(Exception):
        pass

    @given(
        Foo,
        settings=Settings(max_examples=10, database=db))
    def nope(x):
        print(x)
        raise Rejected()
    try:
        with pytest.raises(Rejected):
            nope()  # pragma: no branch
    finally:
        db.close()
