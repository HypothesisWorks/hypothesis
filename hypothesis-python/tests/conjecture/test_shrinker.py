# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import time

import pytest

from hypothesis import HealthCheck, assume, example, given, settings, strategies as st
from hypothesis.internal.conjecture.data import ChoiceNode, ConjectureData
from hypothesis.internal.conjecture.datatree import compute_max_children
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.internal.conjecture.shrinker import (
    Shrinker,
    ShrinkPass,
    StopShrinking,
    node_program,
)
from hypothesis.internal.conjecture.shrinking.common import Shrinker as ShrinkerPass
from hypothesis.internal.conjecture.utils import Sampler
from hypothesis.internal.floats import MAX_PRECISE_INTEGER

from tests.conjecture.common import (
    SOME_LABEL,
    float_constr,
    interesting_origin,
    nodes,
    nodes_inline,
    run_to_nodes,
    shrinking_from,
)


@pytest.mark.parametrize("n", [1, 5, 8, 15])
def test_can_shrink_variable_draws_with_just_deletion(n):
    @shrinking_from((n,) + (0,) * (n - 1) + (1,))
    def shrinker(data: ConjectureData):
        n = data.draw_integer(0, 2**4 - 1)
        b = [data.draw_integer(0, 2**8 - 1) for _ in range(n)]
        if any(b):
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_individual_choices"])
    assert shrinker.choices == (1, 1)


def test_deletion_and_lowering_fails_to_shrink(monkeypatch):
    monkeypatch.setattr(
        Shrinker,
        "shrink",
        lambda self: self.fixate_shrink_passes(["minimize_individual_choices"]),
    )
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.cached_test_function((b"\0",) * 10),
    )

    @run_to_nodes
    def nodes(data):
        for _ in range(10):
            data.draw_bytes(1, 1)
        data.mark_interesting()

    assert tuple(n.value for n in nodes) == (b"\0",) * 10


def test_duplicate_nodes_that_go_away():
    @shrinking_from((1234567, 1234567) + (b"\1",) * (1234567 & 255))
    def shrinker(data: ConjectureData):
        x = data.draw_integer(min_value=0)
        y = data.draw_integer(min_value=0)
        if x != y:
            data.mark_invalid()
        b = [data.draw_bytes(1, 1) for _ in range(x & 255)]
        if len(set(b)) <= 1:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_duplicated_choices"])
    assert shrinker.shrink_target.choices == (0, 0)


def test_accidental_duplication():
    @shrinking_from((12, 12) + (b"\2",) * 12)
    def shrinker(data: ConjectureData):
        x = data.draw_integer(0, 2**8 - 1)
        y = data.draw_integer(0, 2**8 - 1)
        if x != y:
            data.mark_invalid()
        if x < 5:
            data.mark_invalid()
        b = [data.draw_bytes(1, 1) for _ in range(x)]
        if len(set(b)) == 1:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_duplicated_choices"])
    print(shrinker.choices)
    assert shrinker.choices == (5, 5, *([b"\x00"] * 5))


def test_can_zero_subintervals():
    @shrinking_from((3, 0, 0, 0, 1) * 10)
    def shrinker(data: ConjectureData):
        for _ in range(10):
            data.start_span(SOME_LABEL)
            n = data.draw_integer(0, 2**8 - 1)
            for _ in range(n):
                data.draw_integer(0, 2**8 - 1)
            data.stop_span()
            if data.draw_integer(0, 2**8 - 1) != 1:
                return
        data.mark_interesting()

    shrinker.shrink()
    assert shrinker.choices == (0, 1) * 10


def test_can_pass_to_an_indirect_descendant():
    def tree(data):
        data.start_span(label=1)
        n = data.draw_integer(0, 1)
        data.draw_integer(0, 2**8 - 1)
        if n:
            tree(data)
            tree(data)
        data.stop_span(discard=True)

    initial = (1, 10, 0, 0, 1, 0, 0, 10, 0, 0)
    target = (0, 10)
    good = {initial, target}

    @shrinking_from(initial)
    def shrinker(data: ConjectureData):
        tree(data)
        if data.choices in good:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["pass_to_descendant"])
    assert shrinker.choices == target


def test_shrinking_blocks_from_common_offset():
    @shrinking_from((11, 10))
    def shrinker(data: ConjectureData):
        m = data.draw_integer(0, 2**8 - 1)
        n = data.draw_integer(0, 2**8 - 1)
        if abs(m - n) <= 1 and max(m, n) > 0:
            data.mark_interesting()

    shrinker.mark_changed(0)
    shrinker.mark_changed(1)
    shrinker.lower_common_node_offset()
    assert shrinker.choices in {(0, 1), (1, 0)}


def test_handle_empty_draws():
    @run_to_nodes
    def nodes(data):
        while True:
            data.start_span(SOME_LABEL)
            n = data.draw_integer(0, 1)
            data.start_span(SOME_LABEL)
            data.stop_span()
            data.stop_span(discard=n > 0)
            if not n:
                break
        data.mark_interesting()

    assert tuple(n.value for n in nodes) == (0,)


def test_can_reorder_spans():
    # grouped by iteration: (1, 1) (1, 1) (0) (0) (0)
    @shrinking_from((1, 1, 1, 1, 0, 0, 0))
    def shrinker(data: ConjectureData):
        total = 0
        for _ in range(5):
            data.start_span(label=0)
            if data.draw_integer(0, 2**8 - 1):
                total += data.draw_integer(0, 2**9 - 1)
            data.stop_span()
        if total == 2:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["reorder_spans"])
    assert shrinker.choices == (0, 0, 0, 1, 1, 1, 1)


def test_permits_but_ignores_raising_order(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.cached_test_function((1,)),
    )

    monkeypatch.setattr(
        Shrinker, "shrink", lambda self: self.consider_new_nodes(nodes_inline(2))
    )

    @run_to_nodes
    def nodes(data):
        data.draw_integer(0, 3)
        data.mark_interesting()

    assert tuple(n.value for n in nodes) == (1,)


def test_block_deletion_can_delete_short_ranges():
    @shrinking_from([v for i in range(5) for _ in range(i + 1) for v in [i]])
    def shrinker(data: ConjectureData):
        while True:
            n = data.draw_integer(0, 2**16 - 1)
            for _ in range(n):
                if data.draw_integer(0, 2**16 - 1) != n:
                    data.mark_invalid()
            if n == 4:
                data.mark_interesting()

    shrinker.fixate_shrink_passes([node_program("X" * i) for i in range(1, 5)])
    assert shrinker.choices == (4,) * 5


def test_dependent_block_pairs_is_up_to_shrinking_integers():
    # Unit test extracted from a failure in tests/nocover/test_integers.py
    distribution = Sampler([4.0, 8.0, 1.0, 1.0, 0.5])
    sizes = [8, 16, 32, 64, 128]

    @shrinking_from((3, True, 65538, 1))
    def shrinker(data: ConjectureData):
        size = sizes[distribution.sample(data)]
        result = data.draw_integer(0, 2**size - 1)
        sign = (-1) ** (result & 1)
        result = (result >> 1) * sign
        cap = data.draw_integer(0, 2**8 - 1)

        if result >= 32768 and cap == 1:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_individual_choices"])
    assert shrinker.choices == (1, True, 65536, 1)


def test_finding_a_minimal_balanced_binary_tree():
    # Tests iteration while the shape of the thing being iterated over can
    # change. In particular the current example can go from trivial to non
    # trivial.

    def tree(data):
        # Returns height of a binary tree and whether it is height balanced.
        data.start_span(label=0)
        if not data.draw_boolean():
            result = (1, True)
        else:
            h1, b1 = tree(data)
            h2, b2 = tree(data)
            result = (1 + max(h1, h2), b1 and b2 and abs(h1 - h2) <= 1)
        data.stop_span()
        return result

    # Starting from an unbalanced tree of depth six
    @shrinking_from((True,) * 5 + (False,) * 6)
    def shrinker(data: ConjectureData):
        _, b = tree(data)
        if not b:
            data.mark_interesting()

    shrinker.shrink()
    assert shrinker.choices == (True, False, True, False, True, False, False)


def test_node_programs_are_adaptive():
    @shrinking_from((False,) * 1000 + (True,))
    def shrinker(data: ConjectureData):
        while not data.draw_boolean():
            pass
        data.mark_interesting()

    p = shrinker.add_new_pass(node_program("X"))
    shrinker.fixate_shrink_passes([p.name])

    assert len(shrinker.choices) == 1
    assert shrinker.calls <= 60


def test_zero_examples_with_variable_min_size():
    @shrinking_from((255,) * 100)
    def shrinker(data: ConjectureData):
        any_nonzero = False
        for i in range(1, 10):
            any_nonzero |= data.draw_integer(0, 2**i - 1) > 0
        if not any_nonzero:
            data.mark_invalid()
        data.mark_interesting()

    shrinker.shrink()
    assert shrinker.choices == (0,) * 8 + (1,)


def test_zero_contained_examples():
    @shrinking_from((1,) * 8)
    def shrinker(data: ConjectureData):
        for _ in range(4):
            data.start_span(1)
            if data.draw_integer(0, 2**8 - 1) == 0:
                data.mark_invalid()
            data.start_span(1)
            data.draw_integer(0, 2**8 - 1)
            data.stop_span()
            data.stop_span()
        data.mark_interesting()

    shrinker.shrink()
    assert shrinker.choices == (1, 0) * 4


def test_zig_zags_quickly():
    @shrinking_from((255,) * 4)
    def shrinker(data: ConjectureData):
        m = data.draw_integer(0, 2**16 - 1)
        n = data.draw_integer(0, 2**16 - 1)
        if m == 0 or n == 0:
            data.mark_invalid()
        if abs(m - n) <= 1:
            data.mark_interesting(interesting_origin(0))
        # Two different interesting origins for avoiding slipping in the
        # shrinker.
        if abs(m - n) <= 10:
            data.mark_interesting(interesting_origin(1))

    shrinker.fixate_shrink_passes(["minimize_individual_choices"])
    assert shrinker.engine.valid_examples <= 100
    assert shrinker.choices == (1, 1)


@pytest.mark.parametrize(
    "min_value, max_value, forced, shrink_towards, expected",
    [
        # this test disallows interesting values in radius 10 interval around shrink_towards
        # to avoid trivial shrinks messing with things, which is why the expected
        # values are ±10 from shrink_towards.
        (-100, 0, -100, 0, (-10, -10)),
        (-100, 0, -100, -35, (-25, -25)),
        (0, 100, 100, 0, (10, 10)),
        (0, 100, 100, 65, (75, 75)),
    ],
)
def test_zig_zags_quickly_with_shrink_towards(
    min_value, max_value, forced, shrink_towards, expected
):
    # we should be able to efficiently incorporate shrink_towards when dealing
    # with zig zags.

    @shrinking_from((forced,) * 2)
    def shrinker(data: ConjectureData):
        m = data.draw_integer(min_value, max_value, shrink_towards=shrink_towards)
        n = data.draw_integer(min_value, max_value, shrink_towards=shrink_towards)
        # avoid trivial counterexamples
        if abs(m - shrink_towards) < 10 or abs(n - shrink_towards) < 10:
            data.mark_invalid()
        if abs(m - n) <= 1:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_individual_choices"])
    assert shrinker.engine.valid_examples <= 40
    assert shrinker.choices == expected


def test_zero_irregular_examples():
    @shrinking_from((255,) * 6)
    def shrinker(data: ConjectureData):
        data.start_span(1)
        data.draw_integer(0, 2**8 - 1)
        data.draw_integer(0, 2**16 - 1)
        data.stop_span()
        data.start_span(1)
        interesting = (
            data.draw_integer(0, 2**8 - 1) > 0 and data.draw_integer(0, 2**16 - 1) > 0
        )
        data.stop_span()
        if interesting:
            data.mark_interesting()

    shrinker.shrink()
    assert shrinker.choices == (0,) * 2 + (1, 1)


def test_retain_end_of_buffer():
    @shrinking_from((1, 2, 3, 4, 5, 6, 0))
    def shrinker(data: ConjectureData):
        interesting = False
        while True:
            n = data.draw_integer(0, 2**8 - 1)
            if n == 6:
                interesting = True
            if n == 0:
                break
        if interesting:
            data.mark_interesting()

    shrinker.shrink()
    assert shrinker.choices == (6, 0)


def test_can_expand_zeroed_region():
    @shrinking_from((255,) * 5)
    def shrinker(data: ConjectureData):
        seen_non_zero = False
        for _ in range(5):
            if data.draw_integer(0, 2**8 - 1) == 0:
                if seen_non_zero:
                    data.mark_invalid()
            else:
                seen_non_zero = True
        data.mark_interesting()

    shrinker.shrink()
    assert shrinker.choices == (0,) * 5


def test_can_expand_deleted_region():
    @shrinking_from((1, 2, 3, 4, 0, 0))
    def shrinker(data: ConjectureData):
        def t():
            data.start_span(1)

            data.start_span(1)
            m = data.draw_integer(0, 2**8 - 1)
            data.stop_span()

            data.start_span(1)
            n = data.draw_integer(0, 2**8 - 1)
            data.stop_span()

            data.stop_span()
            return (m, n)

        v1 = t()
        if v1 == (1, 2):
            if t() != (3, 4):
                data.mark_invalid()
        if v1 == (0, 0) or t() == (0, 0):
            data.mark_interesting()

    shrinker.shrink()
    assert shrinker.choices == (0, 0)


def test_shrink_pass_method_is_idempotent():
    @shrinking_from((255,))
    def shrinker(data: ConjectureData):
        data.draw_integer(0, 2**8 - 1)
        data.mark_interesting()

    sp = shrinker.shrink_pass(node_program("X"))
    assert isinstance(sp, ShrinkPass)
    assert shrinker.shrink_pass(sp) is sp


def test_will_terminate_stalled_shrinks():
    # Suppress the time based slow shrinking check - we only want
    # the one that checks if we're in a stall where we've shrunk
    # as far as we're going to get.
    time.freeze()

    @shrinking_from((255,) * 100)
    def shrinker(data: ConjectureData):
        count = 0

        for _ in range(100):
            if data.draw_integer(0, 2**8 - 1) != 255:
                count += 1
                if count >= 10:
                    return
        data.mark_interesting()

    shrinker.shrink()
    assert shrinker.calls <= 1 + 2 * shrinker.max_stall


def test_will_let_fixate_shrink_passes_do_a_full_run_through():
    @shrinking_from(list(range(50)))
    def shrinker(data: ConjectureData):
        for i in range(50):
            if data.draw_integer(0, 2**8 - 1) != i:
                data.mark_invalid()
        data.mark_interesting()

    shrinker.max_stall = 5
    passes = [node_program("X" * i) for i in range(1, 11)]
    with pytest.raises(StopShrinking):
        shrinker.fixate_shrink_passes(passes)

    assert shrinker.shrink_pass(passes[-1]).calls > 0


@pytest.mark.parametrize("n_gap", [0, 1, 2])
def test_can_simultaneously_lower_non_duplicated_nearby_integers(n_gap):
    @shrinking_from((1, 1) + (0,) * n_gap + (2,))
    def shrinker(data: ConjectureData):
        # Block off lowering the whole buffer
        if data.draw_integer(0, 2**1 - 1) == 0:
            data.mark_invalid()
        m = data.draw_integer(0, 2**8 - 1)
        for _ in range(n_gap):
            data.draw_integer(0, 2**8 - 1)
        n = data.draw_integer(0, 2**16 - 1)

        if n == m + 1:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["lower_integers_together"])
    assert shrinker.choices == (1, 0) + (0,) * n_gap + (1,)


def test_redistribute_with_forced_node_integer():
    @shrinking_from((15, 10))
    def shrinker(data: ConjectureData):
        n1 = data.draw_integer(0, 100)
        n2 = data.draw_integer(0, 100, forced=10)
        if n1 + n2 > 20:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["redistribute_numeric_pairs"])
    # redistribute_numeric_pairs shouldn't try modifying forced nodes while
    # shrinking. Since the second draw is forced, this isn't possible to shrink
    # with just this pass.
    assert shrinker.choices == (15, 10)


@pytest.mark.parametrize("n", [10, 50, 100, 200])
def test_can_quickly_shrink_to_trivial_collection(n):
    @shrinking_from([b"\x01" * n])
    def shrinker(data: ConjectureData):
        b = data.draw_bytes()
        if len(b) >= n:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_individual_choices"])
    assert shrinker.choices == (b"\x00" * n,)
    assert shrinker.calls < 10


def test_alternative_shrinking_will_lower_to_alternate_value():
    # We want to reject the first integer value we see when shrinking
    # this alternative, because it will be the result of transmuting the
    # bytes value, and we want to ensure that we can find other values
    # there when we detect the shape change.
    seen_int = None

    @shrinking_from((1, b"hello world"))
    def shrinker(data: ConjectureData):
        nonlocal seen_int
        i = data.draw_integer(min_value=0, max_value=1)
        if i == 1:
            if data.draw_bytes():
                data.mark_interesting()
        else:
            n = data.draw_integer(0, 100)
            if n == 0:
                return
            if seen_int is None:
                seen_int = n
            elif n != seen_int:
                data.mark_interesting()

    shrinker.initial_coarse_reduction()
    assert shrinker.choices[0] == 0


class BadShrinker(ShrinkerPass):
    """
    A shrinker that really doesn't do anything at all. This is mostly a covering
    test for the shrinker interface methods.
    """

    def run_step(self):
        return


def test_silly_shrinker_subclass():
    assert BadShrinker.shrink(10, lambda _: True) == 10


numeric_nodes = nodes(choice_types=["integer", "float"])


@given(numeric_nodes, numeric_nodes, st.integers() | st.floats(allow_nan=False))
@example(
    ChoiceNode(
        type="float",
        value=float(MAX_PRECISE_INTEGER - 1),
        constraints=float_constr(),
        was_forced=False,
    ),
    ChoiceNode(
        type="float",
        value=float(MAX_PRECISE_INTEGER - 1),
        constraints=float_constr(),
        was_forced=False,
    ),
    0,
)
@settings(suppress_health_check=[HealthCheck.filter_too_much])
def test_redistribute_numeric_pairs(node1, node2, stop):
    assume(node1.value + node2.value > stop)
    # avoid exhausting the tree while generating, which causes @shrinking_from's
    # runner to raise
    assume(
        compute_max_children(node1.type, node1.constraints)
        + compute_max_children(node2.type, node2.constraints)
        > 2
    )

    @shrinking_from([node1.value, node2.value])
    def shrinker(data: ConjectureData):
        v1 = getattr(data, f"draw_{node1.type}")(**node1.constraints)
        v2 = getattr(data, f"draw_{node2.type}")(**node2.constraints)
        if v1 + v2 > stop:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["redistribute_numeric_pairs"])
    assert len(shrinker.choices) == 2
    # we should always have lowered the first choice and raised the second choice
    # - or left the choices the same.
    assert shrinker.choices[0] <= node1.value
    assert shrinker.choices[1] >= node2.value


@pytest.mark.parametrize(
    "start, expected",
    [
        (("1" * 5, "1" * 5), ("0" * 5, "0" * 5)),
        (("1222344", "1222344"), ("0" * 7, "0" * 7)),
    ],
)
@pytest.mark.parametrize("gap", [0, 1, 2, 3])
def test_lower_duplicated_characters_across_choices(start, expected, gap):
    # the draws from `gap` are irrelevant and only test that we can still shrink
    # duplicated characters from nearby choices even when the choices are not
    # consecutive.
    @shrinking_from([start[0], *([0] * gap), start[1]])
    def shrinker(data: ConjectureData):
        s1 = data.draw(st.text())

        for _ in range(gap):
            data.draw(st.integers())

        s2 = data.draw(st.text())
        if s1 == s2:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["lower_duplicated_characters"])
    assert shrinker.choices == (expected[0],) + (0,) * gap + (expected[1],)


def test_shrinking_one_of_with_same_shape():
    # This is a covering test for our one_of shrinking logic for the case when
    # the choice sequence *doesn't* change shape in the newly chosen one_of branch.
    @shrinking_from([1, 0])
    def shrinker(data: ConjectureData):
        n = data.draw_integer(0, 1)
        data.draw_integer()
        if n == 1:
            data.mark_interesting()

    shrinker.initial_coarse_reduction()
    assert shrinker.choices == (1, 0)
