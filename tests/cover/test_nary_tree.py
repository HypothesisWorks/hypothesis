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

from hypothesis import Settings, given
from hypothesis.strategies import booleans, integers
from hypothesis.internal.debug import minimal
from hypothesis.searchstrategy.narytree import Leaf, Branch, n_ary_tree


def smallest_tree(predicate):
    return minimal(
        n_ary_tree(integers(), integers(), integers()), predicate
    )


def test_tree_minimizes_to_leaf_with_minimal_value():
    assert smallest_tree(lambda t: True) == Leaf(0)


def test_tree_minimizes_number_of_branch_children():
    assert smallest_tree(lambda t: isinstance(t, Branch)) == Branch(
        0, ()
    )


def depth(tree):
    if isinstance(tree, Leaf):
        return 1
    else:
        if not tree.keyed_children:
            return 1
        return 1 + max(depth(v) for k, v in tree.keyed_children)


def test_deep_trees():
    tree = smallest_tree(lambda t: depth(t) >= 3)
    assert depth(tree) == 3
    while isinstance(tree, Branch):
        assert len(tree.keyed_children) == 1
        tree = tree.keyed_children[0][1]


def test_tree_minimizes_individual_branch_children():
    assert smallest_tree(
        lambda t: len(getattr(t, u'keyed_children', ())) > 1) == Branch(
            0, ((0, Leaf(0)), (0, Leaf(0)))
    )


@given(n_ary_tree(booleans(), booleans(), booleans()), settings=Settings(
    max_examples=100
))
def test_serializes_arbitrary_trees(tree):
    strat = n_ary_tree(booleans(), booleans(), booleans())

    assert strat.from_basic(strat.to_basic(tree)) == tree
