# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math
import sys
from copy import deepcopy

import pytest

from hypothesis import HealthCheck, assume, example, given, settings, strategies as st
from hypothesis.errors import StopTest
from hypothesis.internal.conjecture.data import (
    ConjectureData,
    IRNode,
    Status,
    ir_value_equal,
    ir_value_permitted,
)
from hypothesis.internal.conjecture.datatree import (
    MAX_CHILDREN_EFFECTIVELY_INFINITE,
    all_children,
    compute_max_children,
)
from hypothesis.internal.floats import SMALLEST_SUBNORMAL, next_down, next_up
from hypothesis.internal.intervalsets import IntervalSet

from tests.common.debug import minimal
from tests.conjecture.common import fresh_data, ir_types_and_kwargs, kwargs_strategy


def draw_value(ir_type, kwargs):
    data = fresh_data()
    return getattr(data, f"draw_{ir_type}")(**kwargs)


# we max out at 128 bit integers in the *unbounded* case, but someone may
# specify a bound with a larger magnitude. Ensure we calculate max children for
# those cases correctly.
@example(("integer", {"min_value": None, "max_value": -(2**200), "weights": None}))
@example(("integer", {"min_value": 2**200, "max_value": None, "weights": None}))
@example(("integer", {"min_value": -(2**200), "max_value": 2**200, "weights": None}))
@given(ir_types_and_kwargs())
def test_compute_max_children_is_positive(ir_type_and_kwargs):
    (ir_type, kwargs) = ir_type_and_kwargs
    assert compute_max_children(ir_type, kwargs) >= 0


@pytest.mark.parametrize(
    "ir_type, kwargs, count_children",
    [
        ("integer", {"min_value": 1, "max_value": 2, "weights": [0, 1]}, 1),
        ("integer", {"min_value": 1, "max_value": 4, "weights": [0, 0.5, 0, 0.5]}, 2),
        # only possibility is the empty string
        (
            "string",
            {"min_size": 0, "max_size": 100, "intervals": IntervalSet.from_string("")},
            1,
        ),
        (
            "string",
            {"min_size": 0, "max_size": 0, "intervals": IntervalSet.from_string("abc")},
            1,
        ),
        # 3 possibilities for each character, 8 characters, 3 ** 8 possibilities.
        (
            "string",
            {"min_size": 8, "max_size": 8, "intervals": IntervalSet.from_string("abc")},
            3**8,
        ),
        (
            "string",
            {
                "min_size": 2,
                "max_size": 8,
                "intervals": IntervalSet.from_string("abcd"),
            },
            sum(4**k for k in range(2, 8 + 1)),
        ),
        (
            "string",
            {
                "min_size": 0,
                "max_size": None,
                "intervals": IntervalSet.from_string("a"),
            },
            MAX_CHILDREN_EFFECTIVELY_INFINITE,
        ),
        (
            "string",
            {
                "min_size": 0,
                "max_size": 10_000,
                "intervals": IntervalSet.from_string("abcdefg"),
            },
            MAX_CHILDREN_EFFECTIVELY_INFINITE,
        ),
        ("boolean", {"p": 0.0}, 1),
        ("boolean", {"p": 1.0}, 1),
        ("boolean", {"p": 0.5}, 2),
        ("boolean", {"p": 0.001}, 2),
        ("boolean", {"p": 0.999}, 2),
        (
            "float",
            {
                "min_value": 0.0,
                "max_value": 0.0,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            1,
        ),
        (
            "float",
            {
                "min_value": -0.0,
                "max_value": -0.0,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            1,
        ),
        (
            "float",
            {
                "min_value": -0.0,
                "max_value": 0.0,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            2,
        ),
        (
            "float",
            {
                "min_value": next_down(-0.0),
                "max_value": next_up(0.0),
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            4,
        ),
        (
            "float",
            {
                "min_value": next_down(next_down(-0.0)),
                "max_value": next_up(next_up(0.0)),
                "smallest_nonzero_magnitude": next_up(SMALLEST_SUBNORMAL),
            },
            4,
        ),
        (
            "float",
            {
                "min_value": -math.inf,
                "max_value": math.inf,
                "smallest_nonzero_magnitude": next_down(math.inf),
            },
            6,
        ),
        (
            "float",
            {
                "min_value": 1,
                "max_value": 10,
                "smallest_nonzero_magnitude": 11.0,
            },
            0,
        ),
        (
            "float",
            {
                "min_value": -3,
                "max_value": -2,
                "smallest_nonzero_magnitude": 4.0,
            },
            0,
        ),
    ],
)
def test_compute_max_children(ir_type, kwargs, count_children):
    assert compute_max_children(ir_type, kwargs) == count_children


@given(st.text(min_size=1, max_size=1), st.integers(0, 100))
def test_draw_string_single_interval_with_equal_bounds(s, n):
    data = fresh_data()
    intervals = IntervalSet.from_string(s)
    assert data.draw_string(intervals, min_size=n, max_size=n) == s * n


@example(("boolean", {"p": 2**-65}))
@example(("boolean", {"p": 1 - 2**-65}))
@example(
    (
        "string",
        {"min_size": 0, "max_size": 0, "intervals": IntervalSet.from_string("abc")},
    )
)
@example(
    ("string", {"min_size": 0, "max_size": 3, "intervals": IntervalSet.from_string("")})
)
@example(
    (
        "string",
        {"min_size": 0, "max_size": 3, "intervals": IntervalSet.from_string("a")},
    )
)
# all combinations of float signs
@example(
    (
        "float",
        {
            "min_value": next_down(-0.0),
            "max_value": -0.0,
            "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
        },
    )
)
@example(
    (
        "float",
        {
            "min_value": next_down(-0.0),
            "max_value": next_up(0.0),
            "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
        },
    )
)
@example(
    (
        "float",
        {
            "min_value": 0.0,
            "max_value": next_up(0.0),
            "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
        },
    )
)
# using a smallest_nonzero_magnitude which happens to filter out everything
@example(
    ("float", {"min_value": 1.0, "max_value": 2.0, "smallest_nonzero_magnitude": 3.0})
)
@example(
    (
        "integer",
        {
            "min_value": 1,
            "max_value": 2,
            "weights": [0, 1],
            "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
        },
    )
)
@given(ir_types_and_kwargs())
def test_compute_max_children_and_all_children_agree(ir_type_and_kwargs):
    (ir_type, kwargs) = ir_type_and_kwargs
    max_children = compute_max_children(ir_type, kwargs)

    # avoid slowdowns / OOM when reifying extremely large all_children generators.
    # We also hard cap at MAX_CHILDREN_EFFECTIVELY_INFINITE, because max_children
    # returns approximations after this value and so will disagree with
    # all_children.
    cap = min(100_000, MAX_CHILDREN_EFFECTIVELY_INFINITE)
    assume(max_children < cap)
    assert len(list(all_children(ir_type, kwargs))) == max_children


@given(st.randoms())
def test_ir_nodes(random):
    data = fresh_data(random=random)
    data.draw_float(min_value=-10.0, max_value=10.0, forced=5.0)
    data.draw_boolean(forced=True)

    data.start_example(42)
    data.draw_string(IntervalSet.from_string("abcd"), forced="abbcccdddd")
    data.draw_bytes(8, forced=bytes(8))
    data.stop_example()

    data.draw_integer(0, 100, forced=50)

    data.freeze()
    expected_tree_nodes = [
        IRNode(
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
        IRNode(
            ir_type="boolean",
            value=True,
            kwargs={"p": 0.5},
            was_forced=True,
        ),
        IRNode(
            ir_type="string",
            value="abbcccdddd",
            kwargs={
                "intervals": IntervalSet.from_string("abcd"),
                "min_size": 0,
                "max_size": None,
            },
            was_forced=True,
        ),
        IRNode(
            ir_type="bytes",
            value=bytes(8),
            kwargs={"size": 8},
            was_forced=True,
        ),
        IRNode(
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
    assert data.examples.ir_tree_nodes == expected_tree_nodes


@st.composite
def ir_nodes(draw, *, was_forced=None):
    (ir_type, kwargs) = draw(ir_types_and_kwargs())
    value = draw_value(ir_type, kwargs)
    was_forced = draw(st.booleans()) if was_forced is None else was_forced

    return IRNode(ir_type=ir_type, value=value, kwargs=kwargs, was_forced=was_forced)


@given(ir_nodes())
def test_copy_ir_node(node):
    assert node == node

    assume(not node.was_forced)
    new_value = draw_value(node.ir_type, node.kwargs)
    # if we drew the same value as before, the node should still be equal
    assert (node.copy(with_value=new_value) == node) is (
        ir_value_equal(node.ir_type, new_value, node.value)
    )


@given(ir_nodes())
def test_ir_node_equality(node):
    assert node == node
    # for coverage on our NotImplemented return, more than anything.
    assert node != 42


def test_data_with_empty_ir_tree_is_overrun():
    data = ConjectureData.for_ir_tree([])
    with pytest.raises(StopTest):
        data.draw_integer()

    assert data.status is Status.OVERRUN


# root cause of too_slow is filtering too much via assume in kwargs strategies.
# exacerbated in this test because we draw kwargs twice.
# TODO revisit and improve the kwargs strategies at some point, once the ir
# is further along we can maybe remove e.g. a string assumption.
@given(st.data())
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_node_with_different_ir_type_is_invalid(data):
    node = data.draw(ir_nodes())
    (ir_type, kwargs) = data.draw(ir_types_and_kwargs())

    # drawing a node with a different ir type should cause a misalignment.
    assume(ir_type != node.ir_type)

    data = ConjectureData.for_ir_tree([node])
    draw_func = getattr(data, f"draw_{ir_type}")
    with pytest.raises(StopTest):
        draw_func(**kwargs)

    assert data.status is Status.INVALID


@given(st.data())
def test_node_with_same_ir_type_but_different_value_is_invalid(data):
    node = data.draw(ir_nodes())
    kwargs = data.draw(kwargs_strategy(node.ir_type))

    # drawing a node with the same ir type, but a non-compatible value, should
    # also cause a misalignment.
    assume(not ir_value_permitted(node.value, node.ir_type, kwargs))

    data = ConjectureData.for_ir_tree([node])
    draw_func = getattr(data, f"draw_{node.ir_type}")
    with pytest.raises(StopTest):
        draw_func(**kwargs)

    assert data.status is Status.INVALID


@given(st.data())
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_data_with_changed_was_forced(data):
    # we had a normal node and then tried to draw a different forced value from it.
    # ir tree: v1 [was_forced=False]
    # drawing:    [forced=v2]
    node = data.draw(ir_nodes(was_forced=False))
    data = ConjectureData.for_ir_tree([node])

    draw_func = getattr(data, f"draw_{node.ir_type}")
    kwargs = deepcopy(node.kwargs)
    kwargs["forced"] = draw_value(node.ir_type, node.kwargs)
    assume(not ir_value_equal(node.ir_type, kwargs["forced"], node.value))

    assert ir_value_equal(node.ir_type, draw_func(**kwargs), kwargs["forced"])


@given(ir_nodes(was_forced=True))
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_data_with_changed_forced_value(node):
    # we had a forced node and then tried to draw a different forced value from it.
    # ir tree: v1 [was_forced=True]
    # drawing:    [forced=v2]
    #
    # This is actually fine; we'll just ignore the forced node (v1) and return
    # what the draw expects (v2).

    data = ConjectureData.for_ir_tree([node])

    draw_func = getattr(data, f"draw_{node.ir_type}")
    kwargs = deepcopy(node.kwargs)
    kwargs["forced"] = draw_value(node.ir_type, node.kwargs)
    assume(not ir_value_equal(node.ir_type, kwargs["forced"], node.value))

    assert ir_value_equal(node.ir_type, draw_func(**kwargs), kwargs["forced"])


# ensure we hit bare-minimum coverage for all ir types.
@example(
    IRNode(
        ir_type="float",
        value=0.0,
        kwargs={
            "min_value": -math.inf,
            "max_value": math.inf,
            "allow_nan": True,
            "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
        },
        was_forced=True,
    )
)
@example(
    IRNode(
        ir_type="boolean",
        value=False,
        kwargs={"p": 0.5},
        was_forced=True,
    )
)
@example(
    IRNode(
        ir_type="integer",
        value=50,
        kwargs={
            "min_value": 50,
            "max_value": 100,
            "weights": None,
            "shrink_towards": 0,
        },
        was_forced=True,
    )
)
@example(
    IRNode(
        ir_type="string",
        value="aaaa",
        kwargs={
            "intervals": IntervalSet.from_string("bcda"),
            "min_size": 4,
            "max_size": None,
        },
        was_forced=True,
    )
)
@example(
    IRNode(
        ir_type="bytes",
        value=bytes(8),
        kwargs={"size": 8},
        was_forced=True,
    )
)
@given(ir_nodes(was_forced=True))
def test_data_with_same_forced_value_is_valid(node):
    # we had a forced node and then drew the same forced value. This is totally
    # fine!
    # ir tree: v1 [was_forced=True]
    # drawing:    [forced=v1]
    data = ConjectureData.for_ir_tree([node])
    draw_func = getattr(data, f"draw_{node.ir_type}")

    kwargs = deepcopy(node.kwargs)
    kwargs["forced"] = node.value
    assert ir_value_equal(node.ir_type, draw_func(**kwargs), kwargs["forced"])


@given(ir_types_and_kwargs())
def test_all_children_are_permitted_values(ir_type_and_kwargs):
    (ir_type, kwargs) = ir_type_and_kwargs
    max_children = compute_max_children(ir_type, kwargs)

    cap = min(100_000, MAX_CHILDREN_EFFECTIVELY_INFINITE)
    assume(max_children < cap)

    # test that all_children -> ir_value_permitted (but not necessarily the converse.)
    for value in all_children(ir_type, kwargs):
        assert ir_value_permitted(value, ir_type, kwargs), value


@pytest.mark.parametrize(
    "value, ir_type, kwargs, permitted",
    [
        (0, "integer", {"min_value": 1, "max_value": 2}, False),
        (2, "integer", {"min_value": 0, "max_value": 1}, False),
        (10, "integer", {"min_value": 0, "max_value": 20}, True),
        (
            math.nan,
            "float",
            {"min_value": 0.0, "max_value": 0.0, "allow_nan": True},
            True,
        ),
        (
            math.nan,
            "float",
            {"min_value": 0.0, "max_value": 0.0, "allow_nan": False},
            False,
        ),
        (
            2.0,
            "float",
            {
                "min_value": 1.0,
                "max_value": 3.0,
                "allow_nan": True,
                "smallest_nonzero_magnitude": 2.5,
            },
            False,
        ),
        (
            -2.0,
            "float",
            {
                "min_value": -3.0,
                "max_value": -1.0,
                "allow_nan": True,
                "smallest_nonzero_magnitude": 2.5,
            },
            False,
        ),
        (
            1.0,
            "float",
            {
                "min_value": 1.0,
                "max_value": 1.0,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            True,
        ),
        (
            "abcd",
            "string",
            {
                "min_size": 10,
                "max_size": 20,
                "intervals": IntervalSet.from_string("abcd"),
            },
            False,
        ),
        (
            "abcd",
            "string",
            {
                "min_size": 1,
                "max_size": 3,
                "intervals": IntervalSet.from_string("abcd"),
            },
            False,
        ),
        (
            "abcd",
            "string",
            {"min_size": 1, "max_size": 10, "intervals": IntervalSet.from_string("e")},
            False,
        ),
        (
            "e",
            "string",
            {"min_size": 1, "max_size": 10, "intervals": IntervalSet.from_string("e")},
            True,
        ),
        (b"a", "bytes", {"size": 2}, False),
        (b"aa", "bytes", {"size": 2}, True),
        (True, "boolean", {"p": 0}, False),
        (False, "boolean", {"p": 0}, True),
        (True, "boolean", {"p": 1}, True),
        (False, "boolean", {"p": 1}, False),
        (True, "boolean", {"p": 0.5}, True),
        (False, "boolean", {"p": 0.5}, True),
    ],
)
def test_ir_value_permitted(value, ir_type, kwargs, permitted):
    assert ir_value_permitted(value, ir_type, kwargs) == permitted


@given(ir_nodes(was_forced=True))
def test_forced_nodes_are_trivial(node):
    assert node.trivial


@pytest.mark.parametrize(
    "node",
    [
        IRNode(
            ir_type="float",
            value=5.0,
            kwargs={
                "min_value": 5.0,
                "max_value": 10.0,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="float",
            value=0.0,
            kwargs={
                "min_value": -5.0,
                "max_value": 5.0,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="float",
            value=0.0,
            kwargs={
                "min_value": -math.inf,
                "max_value": math.inf,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="boolean",
            value=False,
            kwargs={"p": 0.5},
            was_forced=False,
        ),
        IRNode(
            ir_type="string",
            value="",
            kwargs={
                "intervals": IntervalSet.from_string("abcd"),
                "min_size": 0,
                "max_size": None,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="string",
            value="aaaa",
            kwargs={
                "intervals": IntervalSet.from_string("bcda"),
                "min_size": 4,
                "max_size": None,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="bytes",
            value=bytes(8),
            kwargs={"size": 8},
            was_forced=False,
        ),
        IRNode(
            ir_type="integer",
            value=50,
            kwargs={
                "min_value": 50,
                "max_value": 100,
                "weights": None,
                "shrink_towards": 0,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="integer",
            value=0,
            kwargs={
                "min_value": -10,
                "max_value": 10,
                "weights": None,
                "shrink_towards": 0,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="integer",
            value=2,
            kwargs={
                "min_value": -10,
                "max_value": 10,
                "weights": None,
                "shrink_towards": 2,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="integer",
            value=-10,
            kwargs={
                "min_value": -10,
                "max_value": 10,
                "weights": None,
                "shrink_towards": -12,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="integer",
            value=10,
            kwargs={
                "min_value": -10,
                "max_value": 10,
                "weights": None,
                "shrink_towards": 12,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="integer",
            value=0,
            kwargs={
                "min_value": None,
                "max_value": None,
                "weights": None,
                "shrink_towards": 0,
            },
            was_forced=False,
        ),
    ],
)
def test_trivial_nodes(node):
    assert node.trivial

    @st.composite
    def values(draw):
        data = draw(st.data()).conjecture_data
        return getattr(data, f"draw_{node.ir_type}")(**node.kwargs)

    # if we're trivial, then shrinking should produce the same value.
    assert ir_value_equal(node.ir_type, minimal(values()), node.value)


@pytest.mark.parametrize(
    "node",
    [
        IRNode(
            ir_type="float",
            value=6.0,
            kwargs={
                "min_value": 5.0,
                "max_value": 10.0,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="float",
            value=-5.0,
            kwargs={
                "min_value": -5.0,
                "max_value": 5.0,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="float",
            value=1.0,
            kwargs={
                "min_value": -math.inf,
                "max_value": math.inf,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="boolean",
            value=True,
            kwargs={"p": 0.5},
            was_forced=False,
        ),
        IRNode(
            ir_type="string",
            value="d",
            kwargs={
                "intervals": IntervalSet.from_string("abcd"),
                "min_size": 1,
                "max_size": None,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="bytes",
            value=b"\x01",
            kwargs={"size": 1},
            was_forced=False,
        ),
        IRNode(
            ir_type="integer",
            value=-10,
            kwargs={
                "min_value": -10,
                "max_value": 10,
                "weights": None,
                "shrink_towards": 0,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="integer",
            value=42,
            kwargs={
                "min_value": None,
                "max_value": None,
                "weights": None,
                "shrink_towards": 0,
            },
            was_forced=False,
        ),
    ],
)
def test_nontrivial_nodes(node):
    assert not node.trivial

    @st.composite
    def values(draw):
        data = draw(st.data()).conjecture_data
        return getattr(data, f"draw_{node.ir_type}")(**node.kwargs)

    # if we're nontrivial, then shrinking should produce something different.
    assert not ir_value_equal(node.ir_type, minimal(values()), node.value)


@pytest.mark.parametrize(
    "node",
    [
        IRNode(
            ir_type="float",
            value=1.5,
            kwargs={
                "min_value": 1.1,
                "max_value": 1.6,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="float",
            value=math.floor(sys.float_info.max),
            kwargs={
                "min_value": sys.float_info.max - 1,
                "max_value": math.inf,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="float",
            value=math.ceil(-sys.float_info.max),
            kwargs={
                "min_value": -math.inf,
                "max_value": -sys.float_info.max + 1,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="float",
            value=math.inf,
            kwargs={
                "min_value": math.inf,
                "max_value": math.inf,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="float",
            value=-math.inf,
            kwargs={
                "min_value": -math.inf,
                "max_value": -math.inf,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
            was_forced=False,
        ),
    ],
)
def test_conservative_nontrivial_nodes(node):
    # these nodes actually are trivial, but our analysis doesn't compute them
    # as such. We'd like to improve this in the future!
    assert not node.trivial

    @st.composite
    def values(draw):
        data = draw(st.data()).conjecture_data
        return getattr(data, f"draw_{node.ir_type}")(**node.kwargs)

    assert ir_value_equal(node.ir_type, minimal(values()), node.value)
