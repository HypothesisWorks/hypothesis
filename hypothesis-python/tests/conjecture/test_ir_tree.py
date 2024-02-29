# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given, settings, strategies as st
from hypothesis.internal.conjecture.data import IRTree, IRTreeLeaf
from hypothesis.internal.floats import SMALLEST_SUBNORMAL, float_to_int
from hypothesis.internal.intervalsets import IntervalSet
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    precondition,
    rule,
)

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
def leaves(draw):
    (ir_type, kwargs) = draw(ir_types_and_kwargs())
    return IRTreeLeaf(
        ir_type=ir_type,
        value=draw_ir_value(ir_type, kwargs),
        kwargs=kwargs,
        was_forced=draw(st.booleans()),
        depth=draw(st.integers(min_value=0)),
        index_in_parent=draw(st.integers(min_value=0)),
    )


@given(leaves())
def test_copy_leaf_is_equal(leaf):
    assert leaf == leaf.copy()


@given(leaves())
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
        self.data_strategy = None

    # this init rule is a total hack to allow us to draw from strategies inside
    # @invariant.
    @initialize(data=st.data())
    def set_up_data_strategy(self, data):
        self.data_strategy = data

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

    @precondition(lambda self: len(self.data.ir_tree.leaves()) > 0)
    @invariant()
    def copying_ir_tree_while_replacing_nodes(self):
        tree = self.data.ir_tree
        leaves = tree.leaves()
        i = self.data_strategy.draw(st.integers(0, len(leaves) - 1))
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
