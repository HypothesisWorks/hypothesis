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

from hypothesis import (
    HealthCheck,
    assume,
    example,
    given,
    note,
    settings,
    strategies as st,
)
from hypothesis.errors import StopTest
from hypothesis.internal.conjecture.choice import (
    choice_equal,
    choice_from_index,
    choice_permitted,
    choice_to_index,
    choices_key,
)
from hypothesis.internal.conjecture.data import (
    COLLECTION_DEFAULT_MAX_SIZE,
    ConjectureData,
    IRNode,
    NodeTemplate,
    Status,
    ir_size,
)
from hypothesis.internal.conjecture.datatree import (
    MAX_CHILDREN_EFFECTIVELY_INFINITE,
    all_children,
    compute_max_children,
)
from hypothesis.internal.conjecture.engine import (
    BUFFER_SIZE_IR,
    truncate_choices_to_size,
)
from hypothesis.internal.floats import SMALLEST_SUBNORMAL, next_down, next_up
from hypothesis.internal.intervalsets import IntervalSet

from tests.common.debug import minimal
from tests.conjecture.common import (
    clamped_shrink_towards,
    draw_value,
    float_kw,
    fresh_data,
    integer_kw,
    integer_kwargs,
    ir_nodes,
    ir_types_and_kwargs,
)


# we max out at 128 bit integers in the *unbounded* case, but someone may
# specify a bound with a larger magnitude. Ensure we calculate max children for
# those cases correctly.
@example(("integer", integer_kw(max_value=-(2**200))))
@example(("integer", integer_kw(min_value=2**200)))
@example(("integer", integer_kw(-(2**200), 2**200)))
@given(ir_types_and_kwargs())
def test_compute_max_children_is_positive(ir_type_and_kwargs):
    (ir_type, kwargs) = ir_type_and_kwargs
    assert compute_max_children(ir_type, kwargs) >= 0


@pytest.mark.parametrize(
    "ir_type, kwargs, count_children",
    [
        ("integer", {"min_value": 1, "max_value": 2, "weights": {1: 0.1, 2: 0.1}}, 2),
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
                "max_size": COLLECTION_DEFAULT_MAX_SIZE,
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
        (
            "bytes",
            {
                "min_size": 0,
                "max_size": 2,
            },
            sum(2 ** (8 * k) for k in range(2 + 1)),
        ),
        (
            "bytes",
            {
                "min_size": 0,
                "max_size": COLLECTION_DEFAULT_MAX_SIZE,
            },
            MAX_CHILDREN_EFFECTIVELY_INFINITE,
        ),
        (
            "bytes",
            {
                "min_size": 0,
                "max_size": 10_000,
            },
            MAX_CHILDREN_EFFECTIVELY_INFINITE,
        ),
        ("boolean", {"p": 0.0}, 1),
        ("boolean", {"p": 1.0}, 1),
        ("boolean", {"p": 0.5}, 2),
        ("boolean", {"p": 0.001}, 2),
        ("boolean", {"p": 0.999}, 2),
        ("float", float_kw(0.0, 0.0), 1),
        ("float", float_kw(-0.0, -0.0), 1),
        ("float", float_kw(-0.0, 0.0), 2),
        ("float", float_kw(next_down(-0.0), next_up(0.0)), 4),
        (
            "float",
            float_kw(
                next_down(next_down(-0.0)),
                next_up(next_up(0.0)),
                smallest_nonzero_magnitude=next_up(SMALLEST_SUBNORMAL),
            ),
            4,
        ),
        ("float", float_kw(smallest_nonzero_magnitude=next_down(math.inf)), 6),
        ("float", float_kw(1, 10, smallest_nonzero_magnitude=11.0), 0),
        ("float", float_kw(-3, -2, smallest_nonzero_magnitude=4.0), 0),
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
@example(("float", float_kw(next_down(-0.0), -0.0)))
@example(("float", float_kw(next_down(-0.0), next_up(0.0))))
@example(("float", float_kw(0.0, next_up(0.0))))
# using a smallest_nonzero_magnitude which happens to filter out everything
@example(("float", float_kw(1.0, 2.0, smallest_nonzero_magnitude=3.0)))
@example(("integer", integer_kw(1, 2, weights={1: 0.2, 2: 0.4})))
@given(ir_types_and_kwargs())
@settings(suppress_health_check=[HealthCheck.filter_too_much])
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


# it's very hard to test that unbounded integer ranges agree with
# compute_max_children, because they by necessity require iterating over 2**127
# or more elements. We do the not great approximation of checking just the first
# element is what we expect.


@given(integer_kwargs())
def test_compute_max_children_unbounded_integer_ranges(kwargs):
    expected = clamped_shrink_towards(kwargs)
    first = next(all_children("integer", kwargs))
    assert expected == first, (expected, first)


@given(st.randoms())
def test_ir_nodes(random):
    data = fresh_data(random=random)
    data.draw_float(min_value=-10.0, max_value=10.0, forced=5.0)
    data.draw_boolean(forced=True)

    data.start_example(42)
    data.draw_string(IntervalSet.from_string("abcd"), forced="abbcccdddd")
    data.draw_bytes(8, 8, forced=bytes(8))
    data.stop_example()

    data.draw_integer(0, 100, forced=50)

    data.freeze()
    expected_tree_nodes = (
        IRNode(
            ir_type="float", value=5.0, kwargs=float_kw(-10.0, 10.0), was_forced=True
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
                "max_size": COLLECTION_DEFAULT_MAX_SIZE,
            },
            was_forced=True,
        ),
        IRNode(
            ir_type="bytes",
            value=bytes(8),
            kwargs={"min_size": 8, "max_size": 8},
            was_forced=True,
        ),
        IRNode(ir_type="integer", value=50, kwargs=integer_kw(0, 100), was_forced=True),
    )
    assert data.ir_nodes == expected_tree_nodes


@given(ir_nodes())
def test_copy_ir_node(node):
    assert node == node

    assume(not node.was_forced)
    new_value = draw_value(node.ir_type, node.kwargs)
    # if we drew the same value as before, the node should still be equal
    assert (node.copy(with_value=new_value) == node) is (
        choice_equal(new_value, node.value)
    )


@given(ir_nodes())
def test_ir_node_equality(node):
    assert node == node
    # for coverage on our NotImplemented return, more than anything.
    assert node != 42


@given(ir_nodes(was_forced=True))
def test_cannot_modify_forced_nodes(node):
    with pytest.raises(AssertionError):
        node.copy(with_value=42)


def test_data_with_empty_ir_tree_is_overrun():
    data = ConjectureData.for_choices([])
    with pytest.raises(StopTest):
        data.draw_integer()

    assert data.status is Status.OVERRUN


@given(ir_nodes(was_forced=True))
def test_data_with_changed_forced_value(node):
    # we had a forced node and then tried to draw a different forced value from it.
    # ir tree: v1 [was_forced=True]
    # drawing:    [forced=v2]
    #
    # This is actually fine; we'll just ignore the forced node (v1) and return
    # what the draw expects (v2).

    data = ConjectureData.for_choices([node.value], max_length=BUFFER_SIZE_IR)

    draw_func = getattr(data, f"draw_{node.ir_type}")
    kwargs = deepcopy(node.kwargs)
    kwargs["forced"] = draw_value(node.ir_type, node.kwargs)
    assume(not choice_equal(kwargs["forced"], node.value))

    assert choice_equal(draw_func(**kwargs), kwargs["forced"])


# ensure we hit bare-minimum coverage for all ir types.
@example(IRNode(ir_type="float", value=0.0, kwargs=float_kw(), was_forced=True))
@example(
    IRNode(
        ir_type="boolean",
        value=False,
        kwargs={"p": 0.5},
        was_forced=True,
    )
)
@example(
    IRNode(ir_type="integer", value=50, kwargs=integer_kw(50, 100), was_forced=True)
)
@example(
    IRNode(
        ir_type="string",
        value="aaaa",
        kwargs={
            "intervals": IntervalSet.from_string("bcda"),
            "min_size": 4,
            "max_size": COLLECTION_DEFAULT_MAX_SIZE,
        },
        was_forced=True,
    )
)
@example(
    IRNode(
        ir_type="bytes",
        value=bytes(8),
        kwargs={"min_size": 8, "max_size": 8},
        was_forced=True,
    )
)
@given(ir_nodes(was_forced=True))
def test_data_with_same_forced_value_is_valid(node):
    # we had a forced node and then drew the same forced value. This is totally
    # fine!
    # ir tree: v1 [was_forced=True]
    # drawing:    [forced=v1]
    data = ConjectureData.for_choices([node.value])
    draw_func = getattr(data, f"draw_{node.ir_type}")

    kwargs = deepcopy(node.kwargs)
    kwargs["forced"] = node.value
    assert choice_equal(draw_func(**kwargs), kwargs["forced"])


@given(ir_types_and_kwargs())
@settings(suppress_health_check=[HealthCheck.filter_too_much])
def test_all_children_are_permitted_values(ir_type_and_kwargs):
    (ir_type, kwargs) = ir_type_and_kwargs
    max_children = compute_max_children(ir_type, kwargs)

    cap = min(100_000, MAX_CHILDREN_EFFECTIVELY_INFINITE)
    assume(max_children < cap)

    # test that all_children -> choice_permitted (but not necessarily the converse.)
    for value in all_children(ir_type, kwargs):
        assert choice_permitted(value, kwargs), value


@pytest.mark.parametrize(
    "value, kwargs, permitted",
    [
        (0, integer_kw(1, 2), False),
        (2, integer_kw(0, 1), False),
        (10, integer_kw(0, 20), True),
        (int(2**128 / 2) - 1, integer_kw(), True),
        (int(2**128 / 2), integer_kw(), False),
        (math.nan, float_kw(0.0, 0.0), True),
        (math.nan, float_kw(0.0, 0.0, allow_nan=False), False),
        (2.0, float_kw(1.0, 3.0, smallest_nonzero_magnitude=2.5), False),
        (
            -2.0,
            float_kw(-3.0, -1.0, smallest_nonzero_magnitude=2.5),
            False,
        ),
        (1.0, float_kw(1.0, 1.0), True),
        (
            "abcd",
            {
                "min_size": 10,
                "max_size": 20,
                "intervals": IntervalSet.from_string("abcd"),
            },
            False,
        ),
        (
            "abcd",
            {
                "min_size": 1,
                "max_size": 3,
                "intervals": IntervalSet.from_string("abcd"),
            },
            False,
        ),
        (
            "abcd",
            {"min_size": 1, "max_size": 10, "intervals": IntervalSet.from_string("e")},
            False,
        ),
        (
            "e",
            {"min_size": 1, "max_size": 10, "intervals": IntervalSet.from_string("e")},
            True,
        ),
        (b"a", {"min_size": 2, "max_size": 2}, False),
        (b"aa", {"min_size": 2, "max_size": 2}, True),
        (b"aa", {"min_size": 0, "max_size": 3}, True),
        (b"a", {"min_size": 2, "max_size": 10}, False),
        (True, {"p": 0}, False),
        (False, {"p": 0}, True),
        (True, {"p": 1}, True),
        (False, {"p": 1}, False),
        (True, {"p": 0.5}, True),
        (False, {"p": 0.5}, True),
    ],
)
def test_choice_permitted(value, kwargs, permitted):
    assert choice_permitted(value, kwargs) == permitted


@given(ir_nodes(was_forced=True))
def test_forced_nodes_are_trivial(node):
    assert node.trivial


@pytest.mark.parametrize(
    "node",
    [
        IRNode(
            ir_type="float", value=5.0, kwargs=float_kw(5.0, 10.0), was_forced=False
        ),
        IRNode(
            ir_type="float", value=0.0, kwargs=float_kw(-5.0, 5.0), was_forced=False
        ),
        IRNode(ir_type="float", value=0.0, kwargs=float_kw(), was_forced=False),
        IRNode(ir_type="boolean", value=False, kwargs={"p": 0.5}, was_forced=False),
        IRNode(ir_type="boolean", value=True, kwargs={"p": 1.0}, was_forced=False),
        IRNode(ir_type="boolean", value=False, kwargs={"p": 0.0}, was_forced=False),
        IRNode(
            ir_type="string",
            value="",
            kwargs={
                "intervals": IntervalSet.from_string("abcd"),
                "min_size": 0,
                "max_size": COLLECTION_DEFAULT_MAX_SIZE,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="string",
            value="aaaa",
            kwargs={
                "intervals": IntervalSet.from_string("bcda"),
                "min_size": 4,
                "max_size": COLLECTION_DEFAULT_MAX_SIZE,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="bytes",
            value=bytes(8),
            kwargs={"min_size": 8, "max_size": 8},
            was_forced=False,
        ),
        IRNode(
            ir_type="bytes",
            value=bytes(2),
            kwargs={"min_size": 2, "max_size": COLLECTION_DEFAULT_MAX_SIZE},
            was_forced=False,
        ),
        IRNode(
            ir_type="integer", value=50, kwargs=integer_kw(50, 100), was_forced=False
        ),
        IRNode(
            ir_type="integer", value=0, kwargs=integer_kw(-10, 10), was_forced=False
        ),
        IRNode(
            ir_type="integer",
            value=2,
            kwargs=integer_kw(-10, 10, shrink_towards=2),
            was_forced=False,
        ),
        IRNode(
            ir_type="integer",
            value=-10,
            kwargs=integer_kw(-10, 10, shrink_towards=-12),
            was_forced=False,
        ),
        IRNode(
            ir_type="integer",
            value=10,
            kwargs=integer_kw(-10, 10, shrink_towards=12),
            was_forced=False,
        ),
        IRNode(ir_type="integer", value=0, kwargs=integer_kw(), was_forced=False),
        IRNode(
            ir_type="integer",
            value=1,
            kwargs=integer_kw(min_value=-10, shrink_towards=1),
            was_forced=False,
        ),
        IRNode(
            ir_type="integer",
            value=1,
            kwargs=integer_kw(max_value=10, shrink_towards=1),
            was_forced=False,
        ),
        # TODO_IR: this *is* trivial by node.trivial, but not by shrinking, because
        # the buffer ordering doesn't yet consider shrink_towards for unbounded
        # integers this will be fixed (and this test case can be uncommented) when
        # we move shrink ordering to the typed choice sequence.
        # IRNode(
        #     ir_type="integer",
        #     value=1,
        #     kwargs={
        #         "min_value": None,
        #         "max_value": None,
        #         "weights": None,
        #         "shrink_towards": 1,
        #     },
        #     was_forced=False,
        # ),
    ],
)
def test_trivial_nodes(node):
    assert node.trivial

    @st.composite
    def values(draw):
        data = draw(st.data()).conjecture_data
        return getattr(data, f"draw_{node.ir_type}")(**node.kwargs)

    # if we're trivial, then shrinking should produce the same value.
    assert choice_equal(minimal(values()), node.value)


@pytest.mark.parametrize(
    "node",
    [
        IRNode(
            ir_type="float", value=6.0, kwargs=float_kw(5.0, 10.0), was_forced=False
        ),
        IRNode(
            ir_type="float", value=-5.0, kwargs=float_kw(-5.0, 5.0), was_forced=False
        ),
        IRNode(ir_type="float", value=1.0, kwargs=float_kw(), was_forced=False),
        IRNode(ir_type="boolean", value=True, kwargs={"p": 0.5}, was_forced=False),
        IRNode(ir_type="boolean", value=True, kwargs={"p": 0.99}, was_forced=False),
        IRNode(
            ir_type="string",
            value="d",
            kwargs={
                "intervals": IntervalSet.from_string("abcd"),
                "min_size": 1,
                "max_size": COLLECTION_DEFAULT_MAX_SIZE,
            },
            was_forced=False,
        ),
        IRNode(
            ir_type="bytes",
            value=b"\x01",
            kwargs={"min_size": 1, "max_size": 1},
            was_forced=False,
        ),
        IRNode(
            ir_type="bytes",
            value=bytes(1),
            kwargs={"min_size": 0, "max_size": COLLECTION_DEFAULT_MAX_SIZE},
            was_forced=False,
        ),
        IRNode(
            ir_type="bytes",
            value=bytes(2),
            kwargs={"min_size": 1, "max_size": 10},
            was_forced=False,
        ),
        IRNode(
            ir_type="integer", value=-10, kwargs=integer_kw(-10, 10), was_forced=False
        ),
        IRNode(ir_type="integer", value=42, kwargs=integer_kw(), was_forced=False),
    ],
)
def test_nontrivial_nodes(node):
    assert not node.trivial

    @st.composite
    def values(draw):
        data = draw(st.data()).conjecture_data
        return getattr(data, f"draw_{node.ir_type}")(**node.kwargs)

    # if we're nontrivial, then shrinking should produce something different.
    assert not choice_equal(minimal(values()), node.value)


@pytest.mark.parametrize(
    "node",
    [
        IRNode(
            ir_type="float",
            value=1.5,
            kwargs=float_kw(1.1, 1.6),
            was_forced=False,
        ),
        IRNode(
            ir_type="float",
            value=float(math.floor(sys.float_info.max)),
            kwargs=float_kw(sys.float_info.max - 1, math.inf),
            was_forced=False,
        ),
        IRNode(
            ir_type="float",
            value=float(math.ceil(-sys.float_info.max)),
            kwargs=float_kw(-math.inf, -sys.float_info.max + 1),
            was_forced=False,
        ),
        IRNode(
            ir_type="float",
            value=math.inf,
            kwargs=float_kw(math.inf, math.inf),
            was_forced=False,
        ),
        IRNode(
            ir_type="float",
            value=-math.inf,
            kwargs=float_kw(-math.inf, -math.inf),
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

    assert choice_equal(minimal(values()), node.value)


@given(ir_nodes())
def test_ir_node_is_hashable(ir_node):
    hash(ir_node)


@given(st.lists(ir_nodes()))
def test_ir_size_positive(nodes):
    assert ir_size(nodes) >= 0


@given(st.integers(min_value=1))
def test_node_template_size(n):
    node = NodeTemplate(type="simplest", size=n)
    assert ir_size([node]) == n


@given(st.lists(ir_nodes()), st.integers(min_value=0))
def test_truncate_nodes(nodes, size):
    assert len(truncate_choices_to_size(nodes, size)) <= len(nodes)


def test_node_template_to_overrun():
    data = ConjectureData.for_choices([1, NodeTemplate("simplest", size=10)])
    data.draw_integer()
    with pytest.raises(StopTest):
        for _ in range(10):
            data.draw_integer()

    assert data.status is Status.OVERRUN


def test_node_template_single_node_overruns():
    # test for when drawing a single node takes more than BUFFER_SIZE, while in
    # the NodeTemplate case
    data = ConjectureData.for_choices((NodeTemplate("simplest", size=BUFFER_SIZE_IR),))
    with pytest.raises(StopTest):
        data.draw_bytes(10_000, 10_000)

    assert data.status is Status.OVERRUN


@given(ir_nodes())
def test_node_template_simplest_is_actually_trivial(node):
    # TODO_IR node.trivial is sound but not complete for floats.
    assume(node.ir_type != "float")
    data = ConjectureData.for_choices((NodeTemplate("simplest", size=BUFFER_SIZE_IR),))
    getattr(data, f"draw_{node.ir_type}")(**node.kwargs)
    assert len(data.ir_nodes) == 1
    assert data.ir_nodes[0].trivial


@given(ir_types_and_kwargs())
@example(("boolean", {"p": 0}))
@example(("boolean", {"p": 1}))
def test_choice_indices_are_positive(ir_type_and_kwargs):
    (ir_type, kwargs) = ir_type_and_kwargs
    v = draw_value(ir_type, kwargs)
    assert choice_to_index(v, kwargs) >= 0


@given(integer_kwargs())
def test_shrink_towards_has_index_0(kwargs):
    shrink_towards = clamped_shrink_towards(kwargs)
    note({"clamped_shrink_towards": shrink_towards})
    assert choice_to_index(shrink_towards, kwargs) == 0
    assert choice_from_index(0, "integer", kwargs) == shrink_towards


@given(ir_types_and_kwargs())
def test_choice_to_index_injective(ir_type_and_kwargs):
    # ir ordering should be injective both ways.
    (ir_type, kwargs) = ir_type_and_kwargs
    # ...except for floats, which are hard to order bijectively.
    assume(ir_type != "float")
    # cap to 10k so this test finishes in a reasonable amount of time
    cap = min(compute_max_children(ir_type, kwargs), 10_000)

    indices = set()
    for i, choice in enumerate(all_children(ir_type, kwargs)):
        if i >= cap:
            break
        index = choice_to_index(choice, kwargs)
        assert index not in indices
        indices.add(index)


@given(ir_types_and_kwargs())
@example(
    (
        "string",
        {"min_size": 0, "max_size": 10, "intervals": IntervalSet.from_string("a")},
    )
)
def test_choice_from_value_injective(ir_type_and_kwargs):
    (ir_type, kwargs) = ir_type_and_kwargs
    assume(ir_type != "float")
    cap = min(compute_max_children(ir_type, kwargs), 10_000)

    choices = set()
    for index in range(cap):
        choice = choice_from_index(index, ir_type, kwargs)
        assert choice not in choices
        choices.add(choice)


@given(ir_types_and_kwargs())
def test_choice_index_and_value_are_inverses(ir_type_and_kwargs):
    (ir_type, kwargs) = ir_type_and_kwargs
    v = draw_value(ir_type, kwargs)
    index = choice_to_index(v, kwargs)
    note({"v": v, "index": index})
    choice_equal(choice_from_index(index, ir_type, kwargs), v)


@pytest.mark.parametrize(
    "ir_type, kwargs, choices",
    [
        ("boolean", {"p": 1}, [True]),
        ("boolean", {"p": 0}, [False]),
        ("integer", integer_kw(min_value=1, shrink_towards=4), range(1, 10)),
        ("integer", integer_kw(max_value=5, shrink_towards=2), range(-10, 5 + 1)),
        ("integer", integer_kw(max_value=5), range(-10, 5 + 1)),
        ("integer", integer_kw(min_value=0, shrink_towards=1), range(10)),
        ("integer", integer_kw(-5, 5, shrink_towards=3), range(-5, 5 + 1)),
        ("integer", integer_kw(-5, 5, shrink_towards=-3), range(-5, 5 + 1)),
        (
            "float",
            float_kw(1.0, next_up(next_up(1.0))),
            [1.0, next_up(1.0), next_up(next_up(1.0))],
        ),
        (
            "float",
            float_kw(next_down(-0.0), next_up(0.0)),
            [next_down(-0.0), -0.0, 0.0, next_up(0.0)],
        ),
    ],
)
def test_choice_index_and_value_are_inverses_explicit(ir_type, kwargs, choices):
    for choice in choices:
        index = choice_to_index(choice, kwargs)
        assert choice_equal(choice_from_index(index, ir_type, kwargs), choice)


@pytest.mark.parametrize(
    "kwargs, choices",
    [
        # unbounded
        (integer_kw(), (0, 1, -1, 2, -2, 3, -3)),
        (integer_kw(shrink_towards=2), (2, 3, 1, 4, 0, 5, -1, 6, -2)),
        # semibounded (below)
        (integer_kw(min_value=3), (3, 4, 5, 6, 7)),
        (integer_kw(min_value=3, shrink_towards=5), (5, 6, 4, 7, 3, 8, 9)),
        (integer_kw(min_value=-3), (0, 1, -1, 2, -2, 3, -3, 4, 5, 6)),
        (integer_kw(min_value=-3, shrink_towards=-1), (-1, 0, -2, 1, -3, 2, 3, 4)),
        # semibounded (above)
        (integer_kw(max_value=3), (0, 1, -1, 2, -2, 3, -3, -4, -5, -6)),
        (integer_kw(max_value=3, shrink_towards=1), (1, 2, 0, 3, -1, -2, -3, -4)),
        (integer_kw(max_value=-3), (-3, -4, -5, -6, -7)),
        (integer_kw(max_value=-3, shrink_towards=-5), (-5, -4, -6, -3, -7, -8, -9)),
        # bounded
        (integer_kw(-3, 3), (0, 1, -1, 2, -2, 3, -3)),
        (integer_kw(-3, 3, shrink_towards=1), (1, 2, 0, 3, -1, -2, -3)),
        (integer_kw(-3, 3, shrink_towards=-1), (-1, 0, -2, 1, -3, 2, 3)),
    ],
    ids=repr,
)
def test_integer_choice_index(kwargs, choices):
    # explicit test which checks that the order of `choices` matches the index
    # order.
    for i, choice in enumerate(choices):
        assert choice_to_index(choice, kwargs) == i


@given(st.lists(ir_nodes()))
def test_drawing_directly_matches_for_choices(nodes):
    data = ConjectureData.for_choices([n.value for n in nodes])
    for node in nodes:
        value = getattr(data, f"draw_{node.ir_type}")(**node.kwargs)
        assert choice_equal(node.value, value)


def test_draw_directly_explicit():
    # this is a much weaker and more explicit variant of the property-based test
    # directly above, but this is such an important thing to ensure that we have
    # correct that it's worth some duplication in case we ever screw up our pbt test.
    assert (
        ConjectureData.for_choices(["a"]).draw_string(
            IntervalSet([(0, 127)]), min_size=1
        )
        == "a"
    )
    assert ConjectureData.for_choices([b"a"]).draw_bytes() == b"a"
    assert (
        ConjectureData.for_choices([1.0]).draw_float(
            0.0, 2.0, allow_nan=False, smallest_nonzero_magnitude=0.5
        )
        == 1.0
    )
    assert ConjectureData.for_choices([True]).draw_boolean(0.3)
    assert ConjectureData.for_choices([42]).draw_integer() == 42
    assert (
        ConjectureData.for_choices([-42]).draw_integer(min_value=-50, max_value=0)
        == -42
    )
    assert (
        ConjectureData.for_choices([10]).draw_integer(
            min_value=10, max_value=11, weights={10: 0.1, 11: 0.3}
        )
        == 10
    )


@pytest.mark.parametrize(
    "choices1, choices2",
    [
        [(True,), (1,)],
        [(True,), (1.0,)],
        [(False,), (0,)],
        [(False,), (0.0,)],
        [(False,), (-0.0,)],
        [(0.0,), (-0.0,)],
    ],
)
def test_choices_key_distinguishes_weird_cases(choices1, choices2):
    assert choices_key(choices1) != choices_key(choices2)
