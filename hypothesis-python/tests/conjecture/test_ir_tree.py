# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis.internal.conjecture.data import IRTree, IRTreeLeaf
from hypothesis.internal.floats import SMALLEST_SUBNORMAL
from hypothesis.internal.intervalsets import IntervalSet

from tests.conjecture.common import fresh_data


def test_copy_leaf():
    leaf = IRTreeLeaf(
        ir_type="integer",
        value=10,
        kwargs={"min_value": 0, "max_value": 100, "weights": None, "shrink_towards": 0},
        was_forced=False,
        depth=1,
        index_in_parent=3,
    )
    assert leaf == leaf.copy()


def test_copy_leaf_with_value():
    leaf = IRTreeLeaf(
        ir_type="integer",
        value=10,
        kwargs={"min_value": 0, "max_value": 100, "weights": None, "shrink_towards": 0},
        was_forced=False,
        depth=1,
        index_in_parent=3,
    )
    leaf2 = leaf.copy(with_value=20)
    assert leaf != leaf2
    assert leaf2.value == 20


def test_copy_empty_ir_tree():
    ir_tree = IRTree()
    assert ir_tree.root is None
    assert ir_tree == ir_tree.copy()
    assert ir_tree.copy().root is None


def test_copy_ir_tree():
    data = fresh_data()
    data.draw_boolean(p=0.75)
    data.start_example(42)
    data.draw_integer()
    data.stop_example()

    assert data.ir_tree == data.ir_tree.copy()


def test_copy_ir_tree_replacing_nodes():
    data = fresh_data()
    data.draw_boolean(p=0)
    data.start_example(42)
    data.draw_integer()
    data.stop_example()

    tree = data.ir_tree
    node = tree.leaves()[0]
    assert node.ir_type == "boolean"
    assert node.value is False

    tree2 = tree.copy(replacing_nodes=[(node.location, node.copy(with_value=True))])

    assert tree != tree2
    assert tree2.leaves()[0].value is True


def test_leaves():
    data = fresh_data()
    data.draw_float(min_value=-10.0, max_value=10.0, forced=5.0)
    data.draw_boolean(forced=True)

    data.start_example(42)
    data.draw_string(IntervalSet.from_string("abcd"), forced="abbcccdddd")
    data.draw_bytes(8, forced=bytes(8))
    data.stop_example()

    data.draw_integer(0, 100, forced=50)

    leaves = data.ir_tree.leaves()
    # leaves start at depth 1 due to the top example.
    # index_in_parent counts sub-ir examples too, so they aren't the range(0, 5)
    # you would expect. This will clean up once we get rid of sub-ir examples.
    expected = [
        IRTreeLeaf(
            ir_type="float",
            value=5.0,
            kwargs={
                "min_value": -10.0,
                "max_value": 10.0,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            was_forced=True,
            depth=1,
            index_in_parent=2,
        ),
        IRTreeLeaf(
            ir_type="boolean",
            value=True,
            kwargs={"p": 0.5},
            was_forced=True,
            depth=1,
            index_in_parent=4,
        ),
        IRTreeLeaf(
            ir_type="string",
            value="abbcccdddd",
            kwargs={
                "intervals": IntervalSet.from_string("abcd"),
                "min_size": 0,
                "max_size": None,
            },
            was_forced=True,
            depth=2,
            index_in_parent=12,
        ),
        IRTreeLeaf(
            ir_type="bytes",
            value=bytes(8),
            kwargs={"size": 8},
            was_forced=True,
            depth=2,
            index_in_parent=13,
        ),
        IRTreeLeaf(
            ir_type="integer",
            value=50,
            kwargs={
                "min_value": 0,
                "max_value": 100,
                "weights": None,
                "shrink_towards": 0,
            },
            was_forced=True,
            depth=1,
            index_in_parent=7,
        ),
    ]
    assert leaves == expected
