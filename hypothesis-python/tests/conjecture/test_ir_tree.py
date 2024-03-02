# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.internal.conjecture.data import IRTree, IRTreeLeaf
from hypothesis.internal.floats import SMALLEST_SUBNORMAL, float_to_int
from hypothesis.internal.intervalsets import IntervalSet
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from tests.conjecture.common import (
    draw_boolean_kwargs,
    draw_bytes_kwargs,
    draw_float_kwargs,
    draw_integer_kwargs,
    draw_string_kwargs,
    fresh_data,
    ir_types_and_kwargs,
)


def draw_ir_value(ir_type, kwargs):
    data = fresh_data()
    return getattr(data, f"draw_{ir_type}")(**kwargs)


def ir_value_eq(ir_type, v1, v2):
    if ir_type == "float":
        # correctly handle -0.0 == 0.0 and nan == nan
        return float_to_int(v1) == float_to_int(v2)
    return v1 == v2


@st.composite
def leaves(draw, *, was_forced=None):
    (ir_type, kwargs) = draw(ir_types_and_kwargs())
    return IRTreeLeaf(
        ir_type=ir_type,
        value=draw_ir_value(ir_type, kwargs),
        kwargs=kwargs,
        was_forced=was_forced if was_forced is not None else draw(st.booleans()),
    )


@given(leaves())
def test_copy_leaf_is_equal(leaf):
    assert leaf == leaf.copy()


@given(leaves(was_forced=False))
def test_copy_leaf_with_value(leaf):
    ir_type = leaf.ir_type
    new_value = draw_ir_value(ir_type, leaf.kwargs)
    leaf2 = leaf.copy(with_value=new_value)

    # the copied leaf should have a value of new_value.
    assert ir_value_eq(ir_type, new_value, leaf2.value)
    # if we chose a value different from the original leaf, they should no
    # longer be equal.
    if not ir_value_eq(ir_type, leaf.value, new_value):
        assert leaf != leaf2


@given(leaves(was_forced=True))
def test_copy_forced_leaf_with_value(leaf):
    # we disallow modifying the value of forced leaves while copying for now.
    new_value = draw_ir_value(leaf.ir_type, leaf.kwargs)
    with pytest.raises(AssertionError):
        leaf.copy(with_value=new_value)


def test_copy_empty_ir_tree():
    ir_tree = IRTree()
    assert ir_tree.root is None

    copied = ir_tree.copy()
    assert ir_tree == copied
    assert copied.root is None


# avoid slowdowns or overruns
@settings(max_examples=20, stateful_step_count=10)
class CopyIRTreeIsEqual(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.data = fresh_data()

    @rule(kwargs=draw_integer_kwargs())
    def draw_integer(self, kwargs):
        self.data.draw_integer(**kwargs)

    @rule(kwargs=draw_string_kwargs())
    def draw_string(self, kwargs):
        self.data.draw_string(**kwargs)

    @rule(kwargs=draw_boolean_kwargs())
    def draw_boolean(self, kwargs):
        self.data.draw_boolean(**kwargs)

    @rule(kwargs=draw_bytes_kwargs())
    def draw_bytes(self, kwargs):
        self.data.draw_bytes(**kwargs)

    @rule(kwargs=draw_float_kwargs())
    def draw_float(self, kwargs):
        self.data.draw_float(**kwargs)

    @invariant()
    def copying_ir_tree_is_equal(self):
        assert self.data.ir_tree == self.data.ir_tree.copy()

    @rule(data_strategy=st.data())
    def invariant_copying_ir_tree_while_replacing_nodes(self, data_strategy):
        # this function is morally an invariant, but is implemented as an @rule
        # in order to access st.data() to draw a random leaf.
        if not self.data.ir_tree.leaves():
            return

        tree = self.data.ir_tree
        tree.update_locations()

        leaves = tree.leaves()
        i = data_strategy.draw(st.integers(0, len(leaves) - 1))
        leaf = leaves[i]
        new_value = draw_ir_value(leaf.ir_type, leaf.kwargs)

        tree2 = tree.copy(
            replacing_nodes=[(leaf.location, leaf.copy(with_value=new_value))]
        )
        leaves2 = tree2.leaves()

        assert len(leaves) == len(leaves2)
        assert ir_value_eq(leaf.ir_type, leaves2[i].value, new_value)

        if not ir_value_eq(leaf.ir_type, leaf.value, new_value):
            assert tree != tree2


TestCopyIRTreeIsEqual = CopyIRTreeIsEqual.TestCase


@given(leaves())
def test_new_leaves_have_no_location(leaf):
    assert leaf.location is None
    assert leaf.depth is None
    assert leaf.index_in_parent is None


def test_leaves():
    data = fresh_data()
    data.draw_float(min_value=-10.0, max_value=10.0, forced=5.0)
    data.draw_boolean(forced=True)

    data.start_example(42)
    data.draw_string(IntervalSet.from_string("abcd"), forced="abbcccdddd")
    data.draw_bytes(8, forced=bytes(8))
    data.stop_example()

    data.draw_integer(0, 100, forced=50)

    data.ir_tree.update_locations()
    leaves = data.ir_tree.leaves()
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
        ),
        IRTreeLeaf(
            ir_type="boolean",
            value=True,
            kwargs={"p": 0.5},
            was_forced=True,
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
        ),
        IRTreeLeaf(
            ir_type="bytes",
            value=bytes(8),
            kwargs={"size": 8},
            was_forced=True,
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
        ),
    ]
    assert leaves == expected

    for i, (depth, index_in_parent) in enumerate(
        [(1, 1), (1, 3), (2, 11), (2, 12), (1, 6)]
    ):
        assert leaves[i].location == (depth, index_in_parent)
        assert leaves[i].depth == depth
        assert leaves[i].index_in_parent == index_in_parent
