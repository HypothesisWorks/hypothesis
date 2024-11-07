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

from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.internal.conjecture.shrinker import (
    Shrinker,
    ShrinkPass,
    StopShrinking,
    node_program,
)
from hypothesis.internal.conjecture.utils import Sampler

from tests.conjecture.common import SOME_LABEL, run_to_buffer, shrinking_from


@pytest.mark.parametrize("n", [1, 5, 8, 15])
def test_can_shrink_variable_draws_with_just_deletion(n):
    @shrinking_from([n] + [0] * (n - 1) + [1])
    def shrinker(data: ConjectureData):
        n = data.draw_integer(0, 2**4 - 1)
        b = [data.draw_integer(0, 2**8 - 1) for _ in range(n)]
        if any(b):
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_individual_nodes"])

    assert list(shrinker.shrink_target.buffer) == [1, 1]


def test_deletion_and_lowering_fails_to_shrink(monkeypatch):
    monkeypatch.setattr(
        Shrinker,
        "shrink",
        lambda self: self.fixate_shrink_passes(["minimize_individual_nodes"]),
    )

    def gen(self):
        self.cached_test_function(10)

    monkeypatch.setattr(ConjectureRunner, "generate_new_examples", gen)

    @run_to_buffer
    def x(data):
        for _ in range(10):
            data.draw_bytes(1, 1)
        data.mark_interesting()

    assert x == bytes(10)


def test_duplicate_blocks_that_go_away():
    # careful not to go over 24 bits (> 2**24), which triggers a more complicated
    # interpretation of the buffer in draw_integer due to size sampling.
    @run_to_buffer
    def base_buf(data):
        x = data.draw_integer(0, 2**24 - 1, forced=1234567)
        _y = data.draw_integer(0, 2**24 - 1, forced=1234567)
        for _ in range(x & 255):
            data.draw_bytes(1, 1)
        data.mark_interesting()

    @shrinking_from(base_buf)
    def shrinker(data: ConjectureData):
        x = data.draw_integer(0, 2**24 - 1)
        y = data.draw_integer(0, 2**24 - 1)
        if x != y:
            data.mark_invalid()
        b = [data.draw_bytes(1, 1) for _ in range(x & 255)]
        if len(set(b)) <= 1:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_duplicated_nodes"])
    # 24 bits for each integer = (24 * 2) / 8 = 6 bytes, which should all get
    # reduced to 0.
    assert shrinker.shrink_target.buffer == bytes(6)


def test_accidental_duplication():
    @shrinking_from([18] * 20)
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

    shrinker.fixate_shrink_passes(["minimize_duplicated_nodes"])
    # x=5 y=5 b=[b'\x00', b'\x00', b'\x00', b'\x00', b'\x00']
    assert list(shrinker.buffer) == [5] * 2 + [0] * 5


def test_can_zero_subintervals():
    @shrinking_from(bytes([3, 0, 0, 0, 1]) * 10)
    def shrinker(data: ConjectureData):
        for _ in range(10):
            data.start_example(SOME_LABEL)
            n = data.draw_integer(0, 2**8 - 1)
            for _ in range(n):
                data.draw_integer(0, 2**8 - 1)
            data.stop_example()
            if data.draw_integer(0, 2**8 - 1) != 1:
                return
        data.mark_interesting()

    shrinker.shrink()
    assert list(shrinker.buffer) == [0, 1] * 10


def test_can_pass_to_an_indirect_descendant():
    def tree(data):
        data.start_example(label=1)
        n = data.draw_integer(0, 1)
        data.draw_integer(0, 2**8 - 1)
        if n:
            tree(data)
            tree(data)
        data.stop_example(discard=True)

    initial = bytes([1, 10, 0, 0, 1, 0, 0, 10, 0, 0])
    target = bytes([0, 10])

    good = {initial, target}

    @shrinking_from(initial)
    def shrinker(data: ConjectureData):
        tree(data)
        if bytes(data.buffer) in good:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["pass_to_descendant"])

    assert shrinker.shrink_target.buffer == target


def shrink(buffer, *passes):
    def accept(f):
        shrinker = shrinking_from(buffer)(f)

        shrinker.fixate_shrink_passes(passes)

        return list(shrinker.buffer)

    return accept


def test_shrinking_blocks_from_common_offset():
    @shrinking_from([11, 10])
    def shrinker(data: ConjectureData):
        m = data.draw_integer(0, 2**8 - 1)
        n = data.draw_integer(0, 2**8 - 1)
        if abs(m - n) <= 1 and max(m, n) > 0:
            data.mark_interesting()

    shrinker.mark_changed(0)
    shrinker.mark_changed(1)
    shrinker.lower_common_node_offset()

    x = shrinker.shrink_target.buffer

    assert sorted(x) == [0, 1]


def test_handle_empty_draws():
    @run_to_buffer
    def x(data):
        while True:
            data.start_example(SOME_LABEL)
            n = data.draw_integer(0, 1)
            data.start_example(SOME_LABEL)
            data.stop_example()
            data.stop_example(discard=n > 0)
            if not n:
                break
        data.mark_interesting()

    assert x == bytes([0])


def test_can_reorder_examples():
    # grouped by iteration: (1, 0, 1) (1, 0, 1) (0) (0) (0)
    @shrinking_from([1, 0, 1, 1, 0, 1, 0, 0, 0])
    def shrinker(data: ConjectureData):
        total = 0
        for _ in range(5):
            data.start_example(label=0)
            if data.draw_integer(0, 2**8 - 1):
                total += data.draw_integer(0, 2**9 - 1)
            data.stop_example()
        if total == 2:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["reorder_examples"])

    assert list(shrinker.buffer) == [0, 0, 0, 1, 0, 1, 1, 0, 1]


def test_permits_but_ignores_raising_order(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.cached_test_function([1]),
    )

    monkeypatch.setattr(
        Shrinker, "shrink", lambda self: self.incorporate_new_buffer(bytes([2]))
    )

    @run_to_buffer
    def x(data):
        data.draw_integer(0, 3)
        data.mark_interesting()

    assert list(x) == [1]


def test_block_deletion_can_delete_short_ranges():
    @shrinking_from([v for i in range(5) for _ in range(i + 1) for v in [0, i]])
    def shrinker(data: ConjectureData):
        while True:
            n = data.draw_integer(0, 2**16 - 1)
            for _ in range(n):
                if data.draw_integer(0, 2**16 - 1) != n:
                    data.mark_invalid()
            if n == 4:
                data.mark_interesting()

    shrinker.fixate_shrink_passes([node_program("X" * i) for i in range(1, 5)])
    assert list(shrinker.shrink_target.buffer) == [0, 4] * 5


def test_dependent_block_pairs_is_up_to_shrinking_integers():
    # Unit test extracted from a failure in tests/nocover/test_integers.py
    distribution = Sampler([4.0, 8.0, 1.0, 1.0, 0.5])

    sizes = [8, 16, 32, 64, 128]

    @run_to_buffer
    def buf(data):
        size = sizes[distribution.sample(data, forced=3)]
        result = data.draw_integer(0, 2**size - 1, forced=65538)
        sign = (-1) ** (result & 1)
        result = (result >> 1) * sign
        cap = data.draw_integer(0, 2**8 - 1, forced=1)

        if result >= 32768 and cap == 1:
            data.mark_interesting()

    @shrinking_from(buf)
    def shrinker(data: ConjectureData):
        size = sizes[distribution.sample(data)]
        result = data.draw_integer(0, 2**size - 1)
        sign = (-1) ** (result & 1)
        result = (result >> 1) * sign
        cap = data.draw_integer(0, 2**8 - 1)

        if result >= 32768 and cap == 1:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_individual_nodes"])
    assert list(shrinker.shrink_target.buffer) == [1, 1, 0, 0, 1, 0, 0, 1]


def test_finding_a_minimal_balanced_binary_tree():
    # Tests iteration while the shape of the thing being iterated over can
    # change. In particular the current example can go from trivial to non
    # trivial.

    def tree(data):
        # Returns height of a binary tree and whether it is height balanced.
        data.start_example(label=0)
        if not data.draw_boolean():
            result = (1, True)
        else:
            h1, b1 = tree(data)
            h2, b2 = tree(data)
            result = (1 + max(h1, h2), b1 and b2 and abs(h1 - h2) <= 1)
        data.stop_example()
        return result

    # Starting from an unbalanced tree of depth six
    @shrinking_from([1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
    def shrinker(data: ConjectureData):
        _, b = tree(data)
        if not b:
            data.mark_interesting()

    shrinker.shrink()

    assert list(shrinker.shrink_target.buffer) == [1, 0, 1, 0, 1, 0, 0]


def test_node_programs_are_adaptive():
    @shrinking_from(bytes(1000) + bytes([1]))
    def shrinker(data: ConjectureData):
        while not data.draw_boolean():
            pass
        data.mark_interesting()

    p = shrinker.add_new_pass(node_program("X"))
    shrinker.fixate_shrink_passes([p.name])

    assert len(shrinker.shrink_target.buffer) == 1
    assert shrinker.calls <= 60


def test_zero_examples_with_variable_min_size():
    @shrinking_from(bytes([255]) * 100)
    def shrinker(data: ConjectureData):
        any_nonzero = False
        for i in range(1, 10):
            any_nonzero |= data.draw_integer(0, 2**i - 1) > 0
        if not any_nonzero:
            data.mark_invalid()
        data.mark_interesting()

    shrinker.shrink()
    assert len([d for d in shrinker.shrink_target.blocks if not d.all_zero]) == 1


def test_zero_contained_examples():
    @shrinking_from(bytes([1]) * 8)
    def shrinker(data: ConjectureData):
        for _ in range(4):
            data.start_example(1)
            if data.draw_integer(0, 2**8 - 1) == 0:
                data.mark_invalid()
            data.start_example(1)
            data.draw_integer(0, 2**8 - 1)
            data.stop_example()
            data.stop_example()
        data.mark_interesting()

    shrinker.shrink()
    assert list(shrinker.shrink_target.buffer) == [1, 0] * 4


def test_zig_zags_quickly():
    @shrinking_from(bytes([255]) * 4)
    def shrinker(data: ConjectureData):
        m = data.draw_integer(0, 2**16 - 1)
        n = data.draw_integer(0, 2**16 - 1)
        if m == 0 or n == 0:
            data.mark_invalid()
        if abs(m - n) <= 1:
            data.mark_interesting(0)
        # Two different interesting origins for avoiding slipping in the
        # shrinker.
        if abs(m - n) <= 10:
            data.mark_interesting(1)

    shrinker.fixate_shrink_passes(["minimize_individual_nodes"])
    assert shrinker.engine.valid_examples <= 100
    assert list(shrinker.shrink_target.buffer) == [0, 1, 0, 1]


@pytest.mark.parametrize(
    "min_value, max_value, forced, shrink_towards, expected_values",
    [
        # this test disallows interesting values in radius 10 interval around shrink_towards
        # to avoid trivial shrinks messing with things, which is why the expected
        # values are ±10 from shrink_towards.
        (-100, 0, -100, 0, [-10, -10]),
        (-100, 0, -100, -35, [-25, -25]),
        (0, 100, 100, 0, [10, 10]),
        (0, 100, 100, 65, [75, 75]),
    ],
)
def test_zig_zags_quickly_with_shrink_towards(
    min_value, max_value, forced, shrink_towards, expected_values
):
    # we should be able to efficiently incorporate shrink_towards when dealing
    # with zig zags.

    @run_to_buffer
    def buf(data):
        m = data.draw_integer(
            min_value, max_value, shrink_towards=shrink_towards, forced=forced
        )
        n = data.draw_integer(
            min_value, max_value, shrink_towards=shrink_towards, forced=forced
        )
        if abs(m - n) <= 1:
            data.mark_interesting()

    @shrinking_from(buf)
    def shrinker(data: ConjectureData):
        m = data.draw_integer(min_value, max_value, shrink_towards=shrink_towards)
        n = data.draw_integer(min_value, max_value, shrink_towards=shrink_towards)
        # avoid trivial counterexamples
        if abs(m - shrink_towards) < 10 or abs(n - shrink_towards) < 10:
            data.mark_invalid()
        if abs(m - n) <= 1:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_individual_nodes"])
    assert shrinker.engine.valid_examples <= 40
    assert [node.value for node in shrinker.nodes] == expected_values


def test_zero_irregular_examples():
    @shrinking_from([255] * 6)
    def shrinker(data: ConjectureData):
        data.start_example(1)
        data.draw_integer(0, 2**8 - 1)
        data.draw_integer(0, 2**16 - 1)
        data.stop_example()
        data.start_example(1)
        interesting = (
            data.draw_integer(0, 2**8 - 1) > 0 and data.draw_integer(0, 2**16 - 1) > 0
        )
        data.stop_example()
        if interesting:
            data.mark_interesting()

    shrinker.shrink()
    assert list(shrinker.shrink_target.buffer) == [0] * 3 + [1, 0, 1]


def test_retain_end_of_buffer():
    @shrinking_from([1, 2, 3, 4, 5, 6, 0])
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
    assert list(shrinker.buffer) == [6, 0]


def test_can_expand_zeroed_region():
    @shrinking_from([255] * 5)
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
    assert list(shrinker.shrink_target.buffer) == [0] * 5


def test_can_expand_deleted_region():
    @shrinking_from([1, 2, 3, 4, 0, 0])
    def shrinker(data: ConjectureData):
        def t():
            data.start_example(1)

            data.start_example(1)
            m = data.draw_integer(0, 2**8 - 1)
            data.stop_example()

            data.start_example(1)
            n = data.draw_integer(0, 2**8 - 1)
            data.stop_example()

            data.stop_example()
            return (m, n)

        v1 = t()
        if v1 == (1, 2):
            if t() != (3, 4):
                data.mark_invalid()
        if v1 == (0, 0) or t() == (0, 0):
            data.mark_interesting()

    shrinker.shrink()
    assert list(shrinker.buffer) == [0, 0]


def test_shrink_pass_method_is_idempotent():
    @shrinking_from([255])
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

    @shrinking_from([255] * 100)
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
    @shrinking_from(range(50))
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


@pytest.mark.parametrize("n_gap", [0, 1, 2, 3])
def test_can_simultaneously_lower_non_duplicated_nearby_blocks(n_gap):
    @shrinking_from([1, 1] + [0] * n_gap + [0, 2])
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

    shrinker.fixate_shrink_passes(["lower_blocks_together"])

    assert list(shrinker.buffer) == [1, 0] + [0] * n_gap + [0, 1]


def test_redistribute_integer_pairs_with_forced_node():
    @run_to_buffer
    def buf(data):
        data.draw_integer(0, 100, forced=15)
        data.draw_integer(0, 100, forced=10)
        data.mark_interesting()

    @shrinking_from(buf)
    def shrinker(data: ConjectureData):
        n1 = data.draw_integer(0, 100)
        n2 = data.draw_integer(0, 100, forced=10)
        if n1 + n2 > 20:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["redistribute_integer_pairs"])
    # redistribute_integer_pairs shouldn't try modifying forced nodes while
    # shrinking. Since the second draw is forced, this isn't possible to shrink
    # with just this pass.
    assert shrinker.buffer == buf
