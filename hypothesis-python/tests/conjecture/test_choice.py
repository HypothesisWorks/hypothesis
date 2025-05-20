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
    ChoiceNode,
    ChoiceTemplate,
    choice_equal,
    choice_from_index,
    choice_permitted,
    choice_to_index,
    choices_key,
)
from hypothesis.internal.conjecture.data import (
    COLLECTION_DEFAULT_MAX_SIZE,
    ConjectureData,
    Status,
    choices_size,
)
from hypothesis.internal.conjecture.datatree import (
    MAX_CHILDREN_EFFECTIVELY_INFINITE,
    all_children,
    compute_max_children,
)
from hypothesis.internal.conjecture.engine import choice_count
from hypothesis.internal.floats import SMALLEST_SUBNORMAL, next_down, next_up
from hypothesis.internal.intervalsets import IntervalSet

from tests.common.debug import minimal
from tests.conjecture.common import (
    choice_types_constraints,
    clamped_shrink_towards,
    draw_value,
    float_constr,
    fresh_data,
    integer_constr,
    integer_constraints,
    nodes,
)


# we max out at 128 bit integers in the *unbounded* case, but someone may
# specify a bound with a larger magnitude. Ensure we calculate max children for
# those cases correctly.
@example(("integer", integer_constr(max_value=-(2**200))))
@example(("integer", integer_constr(min_value=2**200)))
@example(("integer", integer_constr(-(2**200), 2**200)))
@given(choice_types_constraints())
def test_compute_max_children_is_positive(choice_type_and_constraints):
    (choice_type, constraints) = choice_type_and_constraints
    assert compute_max_children(choice_type, constraints) >= 0


@pytest.mark.parametrize(
    "choice_type, constraints, count_children",
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
            COLLECTION_DEFAULT_MAX_SIZE + 1,
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
        ("float", float_constr(0.0, 0.0), 1),
        ("float", float_constr(-0.0, -0.0), 1),
        ("float", float_constr(-0.0, 0.0), 2),
        ("float", float_constr(next_down(-0.0), next_up(0.0)), 4),
        (
            "float",
            float_constr(
                next_down(next_down(-0.0)),
                next_up(next_up(0.0)),
                smallest_nonzero_magnitude=next_up(SMALLEST_SUBNORMAL),
            ),
            4,
        ),
        ("float", float_constr(smallest_nonzero_magnitude=next_down(math.inf)), 6),
        ("float", float_constr(1, 10, smallest_nonzero_magnitude=11.0), 0),
        ("float", float_constr(-3, -2, smallest_nonzero_magnitude=4.0), 0),
    ],
)
def test_compute_max_children(choice_type, constraints, count_children):
    assert compute_max_children(choice_type, constraints) == count_children


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
@example(("float", float_constr(next_down(-0.0), -0.0)))
@example(("float", float_constr(next_down(-0.0), next_up(0.0))))
@example(("float", float_constr(0.0, next_up(0.0))))
# using a smallest_nonzero_magnitude which happens to filter out everything
@example(("float", float_constr(1.0, 2.0, smallest_nonzero_magnitude=3.0)))
@example(("integer", integer_constr(1, 2, weights={1: 0.2, 2: 0.4})))
@given(choice_types_constraints())
@settings(suppress_health_check=[HealthCheck.filter_too_much])
def test_compute_max_children_and_all_children_agree(choice_type_and_constraints):
    (choice_type, constraints) = choice_type_and_constraints
    max_children = compute_max_children(choice_type, constraints)

    # avoid slowdowns / OOM when reifying extremely large all_children generators.
    # We also hard cap at MAX_CHILDREN_EFFECTIVELY_INFINITE, because max_children
    # returns approximations after this value and so will disagree with
    # all_children.
    cap = min(100_000, MAX_CHILDREN_EFFECTIVELY_INFINITE)
    assume(max_children < cap)
    assert len(list(all_children(choice_type, constraints))) == max_children


# it's very hard to test that unbounded integer ranges agree with
# compute_max_children, because they by necessity require iterating over 2**127
# or more elements. We do the not great approximation of checking just the first
# element is what we expect.


@given(integer_constraints())
def test_compute_max_children_unbounded_integer_ranges(constraints):
    expected = clamped_shrink_towards(constraints)
    first = next(all_children("integer", constraints))
    assert expected == first, (expected, first)


@given(st.randoms())
def test_nodes(random):
    data = fresh_data(random=random)
    data.draw_float(min_value=-10.0, max_value=10.0, forced=5.0)
    data.draw_boolean(forced=True)

    data.start_span(42)
    data.draw_string(IntervalSet.from_string("abcd"), forced="abbcccdddd")
    data.draw_bytes(8, 8, forced=bytes(8))
    data.stop_span()

    data.draw_integer(0, 100, forced=50)

    data.freeze()
    expected_tree_nodes = (
        ChoiceNode(
            type="float",
            value=5.0,
            constraints=float_constr(-10.0, 10.0),
            was_forced=True,
        ),
        ChoiceNode(
            type="boolean",
            value=True,
            constraints={"p": 0.5},
            was_forced=True,
        ),
        ChoiceNode(
            type="string",
            value="abbcccdddd",
            constraints={
                "intervals": IntervalSet.from_string("abcd"),
                "min_size": 0,
                "max_size": COLLECTION_DEFAULT_MAX_SIZE,
            },
            was_forced=True,
        ),
        ChoiceNode(
            type="bytes",
            value=bytes(8),
            constraints={"min_size": 8, "max_size": 8},
            was_forced=True,
        ),
        ChoiceNode(
            type="integer",
            value=50,
            constraints=integer_constr(0, 100),
            was_forced=True,
        ),
    )
    assert data.nodes == expected_tree_nodes


@given(nodes())
def test_copy_choice_node(node):
    assert node == node

    assume(not node.was_forced)
    new_value = draw_value(node.type, node.constraints)
    # if we drew the same value as before, the node should still be equal
    assert (node.copy(with_value=new_value) == node) is (
        choice_equal(new_value, node.value)
    )


@given(nodes())
def test_choice_node_equality(node):
    assert node == node
    # for coverage on our NotImplemented return, more than anything.
    assert node != 42


@given(nodes(was_forced=True))
def test_cannot_modify_forced_nodes(node):
    with pytest.raises(AssertionError):
        node.copy(with_value=42)


def test_data_with_empty_choices_is_overrun():
    data = ConjectureData.for_choices([])
    with pytest.raises(StopTest):
        data.draw_integer()

    assert data.status is Status.OVERRUN


@given(nodes(was_forced=True))
def test_data_with_changed_forced_value(node):
    # we had a forced node and then tried to draw a different forced value from it.
    # nodes:   v1 [was_forced=True]
    # drawing:    [forced=v2]
    #
    # This is actually fine; we'll just ignore the forced node (v1) and return
    # what the draw expects (v2).

    data = ConjectureData.for_choices([node.value])

    draw_func = getattr(data, f"draw_{node.type}")
    constraints = deepcopy(node.constraints)
    constraints["forced"] = draw_value(node.type, node.constraints)
    assume(not choice_equal(constraints["forced"], node.value))

    assert choice_equal(draw_func(**constraints), constraints["forced"])


# ensure we hit bare-minimum coverage for all choice sequence types.
@example(
    ChoiceNode(type="float", value=0.0, constraints=float_constr(), was_forced=True)
)
@example(
    ChoiceNode(
        type="boolean",
        value=False,
        constraints={"p": 0.5},
        was_forced=True,
    )
)
@example(
    ChoiceNode(
        type="integer", value=50, constraints=integer_constr(50, 100), was_forced=True
    )
)
@example(
    ChoiceNode(
        type="string",
        value="aaaa",
        constraints={
            "intervals": IntervalSet.from_string("bcda"),
            "min_size": 4,
            "max_size": COLLECTION_DEFAULT_MAX_SIZE,
        },
        was_forced=True,
    )
)
@example(
    ChoiceNode(
        type="bytes",
        value=bytes(8),
        constraints={"min_size": 8, "max_size": 8},
        was_forced=True,
    )
)
@given(nodes(was_forced=True))
def test_data_with_same_forced_value_is_valid(node):
    # we had a forced node and then drew the same forced value. This is totally
    # fine!
    # nodes:   v1 [was_forced=True]
    # drawing:    [forced=v1]
    data = ConjectureData.for_choices([node.value])
    draw_func = getattr(data, f"draw_{node.type}")

    constraints = deepcopy(node.constraints)
    constraints["forced"] = node.value
    assert choice_equal(draw_func(**constraints), constraints["forced"])


@given(choice_types_constraints())
@settings(suppress_health_check=[HealthCheck.filter_too_much])
def test_all_children_are_permitted_values(choice_type_and_constraints):
    (choice_type, constraints) = choice_type_and_constraints
    max_children = compute_max_children(choice_type, constraints)

    cap = min(100_000, MAX_CHILDREN_EFFECTIVELY_INFINITE)
    assume(max_children < cap)

    # test that all_children -> choice_permitted (but not necessarily the converse.)
    for value in all_children(choice_type, constraints):
        assert choice_permitted(value, constraints), value


@pytest.mark.parametrize(
    "value, constraints, permitted",
    [
        (0, integer_constr(1, 2), False),
        (2, integer_constr(0, 1), False),
        (10, integer_constr(0, 20), True),
        (int(2**128 / 2) - 1, integer_constr(), True),
        (int(2**128 / 2), integer_constr(), True),
        (math.nan, float_constr(0.0, 0.0), True),
        (math.nan, float_constr(0.0, 0.0, allow_nan=False), False),
        (2.0, float_constr(1.0, 3.0, smallest_nonzero_magnitude=2.5), False),
        (
            -2.0,
            float_constr(-3.0, -1.0, smallest_nonzero_magnitude=2.5),
            False,
        ),
        (1.0, float_constr(1.0, 1.0), True),
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
def test_choice_permitted(value, constraints, permitted):
    assert choice_permitted(value, constraints) == permitted


@given(nodes(was_forced=True))
def test_forced_nodes_are_trivial(node):
    assert node.trivial


@pytest.mark.parametrize(
    "node",
    [
        ChoiceNode(
            type="float",
            value=5.0,
            constraints=float_constr(5.0, 10.0),
            was_forced=False,
        ),
        ChoiceNode(
            type="float",
            value=0.0,
            constraints=float_constr(-5.0, 5.0),
            was_forced=False,
        ),
        ChoiceNode(
            type="float", value=0.0, constraints=float_constr(), was_forced=False
        ),
        ChoiceNode(
            type="boolean", value=False, constraints={"p": 0.5}, was_forced=False
        ),
        ChoiceNode(
            type="boolean", value=True, constraints={"p": 1.0}, was_forced=False
        ),
        ChoiceNode(
            type="boolean", value=False, constraints={"p": 0.0}, was_forced=False
        ),
        ChoiceNode(
            type="string",
            value="",
            constraints={
                "intervals": IntervalSet.from_string("abcd"),
                "min_size": 0,
                "max_size": COLLECTION_DEFAULT_MAX_SIZE,
            },
            was_forced=False,
        ),
        ChoiceNode(
            type="string",
            value="aaaa",
            constraints={
                "intervals": IntervalSet.from_string("bcda"),
                "min_size": 4,
                "max_size": COLLECTION_DEFAULT_MAX_SIZE,
            },
            was_forced=False,
        ),
        ChoiceNode(
            type="bytes",
            value=bytes(8),
            constraints={"min_size": 8, "max_size": 8},
            was_forced=False,
        ),
        ChoiceNode(
            type="bytes",
            value=bytes(2),
            constraints={"min_size": 2, "max_size": COLLECTION_DEFAULT_MAX_SIZE},
            was_forced=False,
        ),
        ChoiceNode(
            type="integer",
            value=50,
            constraints=integer_constr(50, 100),
            was_forced=False,
        ),
        ChoiceNode(
            type="integer",
            value=0,
            constraints=integer_constr(-10, 10),
            was_forced=False,
        ),
        ChoiceNode(
            type="integer",
            value=2,
            constraints=integer_constr(-10, 10, shrink_towards=2),
            was_forced=False,
        ),
        ChoiceNode(
            type="integer",
            value=-10,
            constraints=integer_constr(-10, 10, shrink_towards=-12),
            was_forced=False,
        ),
        ChoiceNode(
            type="integer",
            value=10,
            constraints=integer_constr(-10, 10, shrink_towards=12),
            was_forced=False,
        ),
        ChoiceNode(
            type="integer", value=0, constraints=integer_constr(), was_forced=False
        ),
        ChoiceNode(
            type="integer",
            value=1,
            constraints=integer_constr(min_value=-10, shrink_towards=1),
            was_forced=False,
        ),
        ChoiceNode(
            type="integer",
            value=1,
            constraints=integer_constr(max_value=10, shrink_towards=1),
            was_forced=False,
        ),
        ChoiceNode(
            type="integer",
            value=1,
            constraints={
                "min_value": None,
                "max_value": None,
                "weights": None,
                "shrink_towards": 1,
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
        return getattr(data, f"draw_{node.type}")(**node.constraints)

    # if we're trivial, then shrinking should produce the same value.
    assert choice_equal(minimal(values()), node.value)


@pytest.mark.parametrize(
    "node",
    [
        ChoiceNode(
            type="float",
            value=6.0,
            constraints=float_constr(5.0, 10.0),
            was_forced=False,
        ),
        ChoiceNode(
            type="float",
            value=-5.0,
            constraints=float_constr(-5.0, 5.0),
            was_forced=False,
        ),
        ChoiceNode(
            type="float", value=1.0, constraints=float_constr(), was_forced=False
        ),
        ChoiceNode(
            type="boolean", value=True, constraints={"p": 0.5}, was_forced=False
        ),
        ChoiceNode(
            type="boolean", value=True, constraints={"p": 0.99}, was_forced=False
        ),
        ChoiceNode(
            type="string",
            value="d",
            constraints={
                "intervals": IntervalSet.from_string("abcd"),
                "min_size": 1,
                "max_size": COLLECTION_DEFAULT_MAX_SIZE,
            },
            was_forced=False,
        ),
        ChoiceNode(
            type="bytes",
            value=b"\x01",
            constraints={"min_size": 1, "max_size": 1},
            was_forced=False,
        ),
        ChoiceNode(
            type="bytes",
            value=bytes(1),
            constraints={"min_size": 0, "max_size": COLLECTION_DEFAULT_MAX_SIZE},
            was_forced=False,
        ),
        ChoiceNode(
            type="bytes",
            value=bytes(2),
            constraints={"min_size": 1, "max_size": 10},
            was_forced=False,
        ),
        ChoiceNode(
            type="integer",
            value=-10,
            constraints=integer_constr(-10, 10),
            was_forced=False,
        ),
        ChoiceNode(
            type="integer", value=42, constraints=integer_constr(), was_forced=False
        ),
    ],
)
def test_nontrivial_nodes(node):
    assert not node.trivial

    @st.composite
    def values(draw):
        data = draw(st.data()).conjecture_data
        return getattr(data, f"draw_{node.type}")(**node.constraints)

    # if we're nontrivial, then shrinking should produce something different.
    assert not choice_equal(minimal(values()), node.value)


@pytest.mark.parametrize(
    "node",
    [
        ChoiceNode(
            type="float",
            value=1.5,
            constraints=float_constr(1.1, 1.6),
            was_forced=False,
        ),
        ChoiceNode(
            type="float",
            value=float(math.floor(sys.float_info.max)),
            constraints=float_constr(sys.float_info.max - 1, math.inf),
            was_forced=False,
        ),
        ChoiceNode(
            type="float",
            value=float(math.ceil(-sys.float_info.max)),
            constraints=float_constr(-math.inf, -sys.float_info.max + 1),
            was_forced=False,
        ),
        ChoiceNode(
            type="float",
            value=math.inf,
            constraints=float_constr(math.inf, math.inf),
            was_forced=False,
        ),
        ChoiceNode(
            type="float",
            value=-math.inf,
            constraints=float_constr(-math.inf, -math.inf),
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
        return getattr(data, f"draw_{node.type}")(**node.constraints)

    assert choice_equal(minimal(values()), node.value)


@given(nodes())
def test_choice_node_is_hashable(node):
    hash(node)


@given(st.lists(nodes()))
def test_choices_size_positive(nodes):
    assert choices_size([n.value for n in nodes]) >= 0


@given(st.integers(min_value=1))
def test_node_template_count(n):
    node = ChoiceTemplate(type="simplest", count=n)
    assert choice_count([node]) == n


def test_node_template_to_overrun():
    data = ConjectureData.for_choices([1, ChoiceTemplate("simplest", count=5)])
    data.draw_integer()
    with pytest.raises(StopTest):
        for _ in range(10):
            data.draw_integer()

    assert data.status is Status.OVERRUN


def test_node_template_single_node_overruns():
    # test for when drawing a single node takes more than BUFFER_SIZE, while in
    # the ChoiceTemplate case
    data = ConjectureData.for_choices((ChoiceTemplate("simplest", count=1),))
    with pytest.raises(StopTest):
        data.draw_bytes(10_000, 10_000)

    assert data.status is Status.OVERRUN


@given(nodes())
def test_node_template_simplest_is_actually_trivial(node):
    # TODO_IR node.trivial is sound but not complete for floats.
    assume(node.type != "float")
    data = ConjectureData.for_choices((ChoiceTemplate("simplest", count=1),))
    getattr(data, f"draw_{node.type}")(**node.constraints)
    assert len(data.nodes) == 1
    assert data.nodes[0].trivial


@given(choice_types_constraints())
@example(("boolean", {"p": 0}))
@example(("boolean", {"p": 1}))
def test_choice_indices_are_positive(choice_type_and_constraints):
    (choice_type, constraints) = choice_type_and_constraints
    v = draw_value(choice_type, constraints)
    assert choice_to_index(v, constraints) >= 0


@given(integer_constraints())
def test_shrink_towards_has_index_0(constraints):
    shrink_towards = clamped_shrink_towards(constraints)
    note({"clamped_shrink_towards": shrink_towards})
    assert choice_to_index(shrink_towards, constraints) == 0
    assert choice_from_index(0, "integer", constraints) == shrink_towards


@given(choice_types_constraints())
def test_choice_to_index_injective(choice_type_and_constraints):
    # choice sequence ordering should be injective both ways.
    (choice_type, constraints) = choice_type_and_constraints
    # ...except for floats, which are hard to order bijectively.
    assume(choice_type != "float")
    # cap to 10k so this test finishes in a reasonable amount of time
    cap = min(compute_max_children(choice_type, constraints), 10_000)

    indices = set()
    for i, choice in enumerate(all_children(choice_type, constraints)):
        if i >= cap:
            break
        index = choice_to_index(choice, constraints)
        assert index not in indices
        indices.add(index)


@given(choice_types_constraints())
@example(
    (
        "string",
        {"min_size": 0, "max_size": 10, "intervals": IntervalSet.from_string("a")},
    )
)
def test_choice_from_value_injective(choice_type_and_constraints):
    (choice_type, constraints) = choice_type_and_constraints
    assume(choice_type != "float")
    cap = min(compute_max_children(choice_type, constraints), 10_000)

    choices = set()
    for index in range(cap):
        choice = choice_from_index(index, choice_type, constraints)
        assert choice not in choices
        choices.add(choice)


@given(choice_types_constraints())
def test_choice_index_and_value_are_inverses(choice_type_and_constraints):
    (choice_type, constraints) = choice_type_and_constraints
    v = draw_value(choice_type, constraints)
    index = choice_to_index(v, constraints)
    note({"v": v, "index": index})
    choice_equal(choice_from_index(index, choice_type, constraints), v)


@pytest.mark.parametrize(
    "choice_type, constraints, choices",
    [
        ("boolean", {"p": 1}, [True]),
        ("boolean", {"p": 0}, [False]),
        ("integer", integer_constr(min_value=1, shrink_towards=4), range(1, 10)),
        ("integer", integer_constr(max_value=5, shrink_towards=2), range(-10, 5 + 1)),
        ("integer", integer_constr(max_value=5), range(-10, 5 + 1)),
        ("integer", integer_constr(min_value=0, shrink_towards=1), range(10)),
        ("integer", integer_constr(-5, 5, shrink_towards=3), range(-5, 5 + 1)),
        ("integer", integer_constr(-5, 5, shrink_towards=-3), range(-5, 5 + 1)),
        (
            "float",
            float_constr(1.0, next_up(next_up(1.0))),
            [1.0, next_up(1.0), next_up(next_up(1.0))],
        ),
        (
            "float",
            float_constr(next_down(-0.0), next_up(0.0)),
            [next_down(-0.0), -0.0, 0.0, next_up(0.0)],
        ),
    ],
)
def test_choice_index_and_value_are_inverses_explicit(
    choice_type, constraints, choices
):
    for choice in choices:
        index = choice_to_index(choice, constraints)
        assert choice_equal(choice_from_index(index, choice_type, constraints), choice)


@pytest.mark.parametrize(
    "constraints, choices",
    [
        # unbounded
        (integer_constr(), (0, 1, -1, 2, -2, 3, -3)),
        (integer_constr(shrink_towards=2), (2, 3, 1, 4, 0, 5, -1, 6, -2)),
        # semibounded (below)
        (integer_constr(min_value=3), (3, 4, 5, 6, 7)),
        (integer_constr(min_value=3, shrink_towards=5), (5, 6, 4, 7, 3, 8, 9)),
        (integer_constr(min_value=-3), (0, 1, -1, 2, -2, 3, -3, 4, 5, 6)),
        (integer_constr(min_value=-3, shrink_towards=-1), (-1, 0, -2, 1, -3, 2, 3, 4)),
        # semibounded (above)
        (integer_constr(max_value=3), (0, 1, -1, 2, -2, 3, -3, -4, -5, -6)),
        (integer_constr(max_value=3, shrink_towards=1), (1, 2, 0, 3, -1, -2, -3, -4)),
        (integer_constr(max_value=-3), (-3, -4, -5, -6, -7)),
        (integer_constr(max_value=-3, shrink_towards=-5), (-5, -4, -6, -3, -7, -8, -9)),
        # bounded
        (integer_constr(-3, 3), (0, 1, -1, 2, -2, 3, -3)),
        (integer_constr(-3, 3, shrink_towards=1), (1, 2, 0, 3, -1, -2, -3)),
        (integer_constr(-3, 3, shrink_towards=-1), (-1, 0, -2, 1, -3, 2, 3)),
    ],
    ids=repr,
)
def test_integer_choice_index(constraints, choices):
    # explicit test which checks that the order of `choices` matches the index
    # order.
    for i, choice in enumerate(choices):
        assert choice_to_index(choice, constraints) == i


@given(st.lists(nodes()))
def test_drawing_directly_matches_for_choices(nodes):
    data = ConjectureData.for_choices([n.value for n in nodes])
    for node in nodes:
        value = getattr(data, f"draw_{node.type}")(**node.constraints)
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


def test_node_template_overrun():
    # different code path for overruning the ChoiceTemplate count, not BUFFER_SIZE.
    cd = ConjectureData(
        random=None,
        prefix=[ChoiceTemplate("simplest", count=2)],
        max_choices=100,
    )

    cd.draw_integer()
    cd.draw_integer()
    try:
        cd.draw_integer()
    except StopTest:
        pass
    assert cd.status is Status.OVERRUN
