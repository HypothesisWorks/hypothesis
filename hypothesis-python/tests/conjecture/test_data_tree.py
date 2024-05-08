# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import textwrap
from random import Random

import pytest

from hypothesis import HealthCheck, assume, given, settings, strategies as st
from hypothesis.errors import Flaky
from hypothesis.internal.conjecture.data import ConjectureData, Status, StopTest
from hypothesis.internal.conjecture.datatree import (
    Branch,
    DataTree,
    compute_max_children,
)
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.internal.conjecture.floats import float_to_int
from hypothesis.internal.escalation import InterestingOrigin
from hypothesis.internal.floats import next_up
from hypothesis.vendor import pretty

from tests.conjecture.common import (
    draw_boolean_kwargs,
    draw_bytes_kwargs,
    draw_float_kwargs,
    draw_integer_kwargs,
    draw_string_kwargs,
    fresh_data,
    ir_nodes,
    run_to_buffer,
)

TEST_SETTINGS = settings(
    max_examples=5000, database=None, suppress_health_check=list(HealthCheck)
)


def runner_for(*examples):
    if len(examples) == 1 and isinstance(examples[0], list):
        examples = examples[0]

    def accept(tf):
        runner = ConjectureRunner(tf, settings=TEST_SETTINGS, random=Random(0))
        runner.exit_with = lambda reason: None
        ran_examples = []
        for e in examples:
            e = bytes(e)
            data = runner.cached_test_function(e)
            ran_examples.append((e, data))
        for e, d in ran_examples:
            rewritten, status = runner.tree.rewrite(e)
            assert status == d.status
            assert rewritten == d.buffer
        return runner

    return accept


def test_can_lookup_cached_examples():
    @runner_for(b"\0\0", b"\0\1")
    def runner(data):
        data.draw_integer(0, 2**8 - 1)
        data.draw_integer(0, 2**8 - 1)


def test_can_lookup_cached_examples_with_forced():
    @runner_for(b"\0\0", b"\0\1")
    def runner(data):
        data.draw_integer(0, 2**8 - 1, forced=1)
        data.draw_integer(0, 2**8 - 1)


def test_can_detect_when_tree_is_exhausted():
    @runner_for(b"\0", b"\1")
    def runner(data):
        data.draw_boolean()

    assert runner.tree.is_exhausted


def test_can_detect_when_tree_is_exhausted_variable_size():
    @runner_for(b"\0", b"\1\0", b"\1\1")
    def runner(data):
        if data.draw_boolean():
            data.draw_integer(0, 1)

    assert runner.tree.is_exhausted


def test_one_dead_branch():
    @runner_for([[0, i] for i in range(16)] + [[i] for i in range(1, 16)])
    def runner(data):
        i = data.draw_integer(0, 15)
        if i > 0:
            data.mark_invalid()
        data.draw_integer(0, 15)

    assert runner.tree.is_exhausted


def test_non_dead_root():
    @runner_for(b"\0\0", b"\1\0", b"\1\1")
    def runner(data):
        data.draw_boolean()
        data.draw_boolean()


def test_can_reexecute_dead_examples():
    @runner_for(b"\0\0", b"\0\1", b"\0\0")
    def runner(data):
        data.draw_boolean()
        data.draw_boolean()


def test_novel_prefixes_are_novel():
    def tf(data):
        for _ in range(4):
            data.draw_bytes(1, forced=b"\0")
            data.draw_integer(0, 3)

    runner = ConjectureRunner(tf, settings=TEST_SETTINGS, random=Random(0))
    for _ in range(100):
        prefix = runner.tree.generate_novel_prefix(runner.random)
        example = prefix + bytes(8 - len(prefix))
        assert runner.tree.rewrite(example)[1] is None
        result = runner.cached_test_function(example)
        assert runner.tree.rewrite(example)[0] == result.buffer


def test_overruns_if_not_enough_bytes_for_block():
    runner = ConjectureRunner(
        lambda data: data.draw_bytes(2), settings=TEST_SETTINGS, random=Random(0)
    )
    runner.cached_test_function(b"\0\0")
    assert runner.tree.rewrite(b"\0")[1] == Status.OVERRUN


def test_overruns_if_prefix():
    runner = ConjectureRunner(
        lambda data: [data.draw_boolean() for _ in range(2)],
        settings=TEST_SETTINGS,
        random=Random(0),
    )
    runner.cached_test_function(b"\0\0")
    assert runner.tree.rewrite(b"\0")[1] == Status.OVERRUN


def test_stores_the_tree_flat_until_needed():
    @runner_for(bytes(10))
    def runner(data):
        for _ in range(10):
            data.draw_boolean()
        data.mark_interesting()

    root = runner.tree.root
    assert len(root.kwargs) == 10
    assert len(root.values) == 10
    assert root.transition.status == Status.INTERESTING


def test_split_in_the_middle():
    @runner_for([0, 0, 2], [0, 1, 3])
    def runner(data):
        data.draw_integer(0, 1)
        data.draw_integer(0, 1)
        data.draw_integer(0, 15)
        data.mark_interesting()

    root = runner.tree.root
    assert len(root.kwargs) == len(root.values) == 1
    assert list(root.transition.children[0].values) == [2]
    assert list(root.transition.children[1].values) == [3]


def test_stores_forced_nodes():
    @runner_for(bytes(3))
    def runner(data):
        data.draw_integer(0, 1, forced=0)
        data.draw_integer(0, 1)
        data.draw_integer(0, 1, forced=0)
        data.mark_interesting()

    root = runner.tree.root
    assert root.forced == {0, 2}


def test_correctly_relocates_forced_nodes():
    @runner_for([0, 0], [1, 0])
    def runner(data):
        data.draw_integer(0, 1)
        data.draw_integer(0, 1, forced=0)
        data.mark_interesting()

    root = runner.tree.root
    assert root.transition.children[1].forced == {0}
    assert root.transition.children[0].forced == {0}


def test_can_go_from_interesting_to_valid():
    tree = DataTree()
    data = ConjectureData.for_buffer(b"", observer=tree.new_observer())
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"", observer=tree.new_observer())
    with pytest.raises(StopTest):
        data.conclude_test(Status.VALID)


def test_going_from_interesting_to_invalid_is_flaky():
    tree = DataTree()
    data = ConjectureData.for_buffer(b"", observer=tree.new_observer())
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"", observer=tree.new_observer())
    with pytest.raises(Flaky):
        data.conclude_test(Status.INVALID)


def test_concluding_at_prefix_is_flaky():
    tree = DataTree()
    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    data.draw_integer(0, 1)
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"", observer=tree.new_observer())
    with pytest.raises(Flaky):
        data.conclude_test(Status.INVALID)


def test_concluding_with_overrun_at_prefix_is_not_flaky():
    tree = DataTree()
    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    data.draw_integer(0, 1)
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"", observer=tree.new_observer())
    with pytest.raises(StopTest):
        data.conclude_test(Status.OVERRUN)


def test_changing_n_bits_is_flaky_in_prefix():
    tree = DataTree()
    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    data.draw_integer(0, 1)
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    with pytest.raises(Flaky):
        data.draw_integer(0, 3)


def test_changing_n_bits_is_flaky_in_branch():
    tree = DataTree()

    for i in [0, 1]:
        data = ConjectureData.for_buffer([i], observer=tree.new_observer())
        data.draw_integer(0, 1)
        with pytest.raises(StopTest):
            data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    with pytest.raises(Flaky):
        data.draw_integer(0, 3)


def test_extending_past_conclusion_is_flaky():
    tree = DataTree()
    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    data.draw_integer(0, 1)
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"\1\0", observer=tree.new_observer())
    data.draw_integer(0, 1)

    with pytest.raises(Flaky):
        data.draw_integer(0, 1)


def test_changing_to_forced_is_flaky():
    tree = DataTree()
    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    data.draw_integer(0, 1)
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"\1\0", observer=tree.new_observer())

    with pytest.raises(Flaky):
        data.draw_integer(0, 1, forced=0)


def test_changing_value_of_forced_is_flaky():
    tree = DataTree()
    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    data.draw_integer(0, 1, forced=1)
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"\1\0", observer=tree.new_observer())

    with pytest.raises(Flaky):
        data.draw_integer(0, 1, forced=0)


def test_does_not_truncate_if_unseen():
    tree = DataTree()
    b = bytes([1, 2, 3, 4])
    assert tree.rewrite(b) == (b, None)


def test_truncates_if_seen():
    tree = DataTree()

    b = bytes([1, 2, 3, 4])

    data = ConjectureData.for_buffer(b, observer=tree.new_observer())
    data.draw_bytes(1)
    data.draw_bytes(1)
    data.freeze()

    assert tree.rewrite(b) == (b[:2], Status.VALID)


def test_child_becomes_exhausted_after_split():
    tree = DataTree()
    data = ConjectureData.for_buffer([0, 0], observer=tree.new_observer())
    data.draw_bytes(1)
    data.draw_bytes(1, forced=b"\0")
    data.freeze()

    data = ConjectureData.for_buffer([1, 0], observer=tree.new_observer())
    data.draw_bytes(1)
    data.draw_bytes(1)
    data.freeze()

    assert not tree.is_exhausted
    assert tree.root.transition.children[b"\0"].is_exhausted


def test_will_generate_novel_prefix_to_avoid_exhausted_branches():
    tree = DataTree()
    data = ConjectureData.for_buffer([1], observer=tree.new_observer())
    data.draw_integer(0, 1)
    data.freeze()

    data = ConjectureData.for_buffer([0, 1], observer=tree.new_observer())
    data.draw_integer(0, 1)
    data.draw_bytes(1)
    data.freeze()

    prefix = list(tree.generate_novel_prefix(Random(0)))

    assert len(prefix) == 2
    assert prefix[0] == 0


def test_will_mark_changes_in_discard_as_flaky():
    tree = DataTree()
    data = ConjectureData.for_buffer([1, 1], observer=tree.new_observer())
    data.start_example(10)
    data.draw_integer(0, 1)
    data.stop_example()
    data.draw_integer(0, 1)
    data.freeze()

    data = ConjectureData.for_buffer([1, 1], observer=tree.new_observer())
    data.start_example(10)
    data.draw_integer(0, 1)

    with pytest.raises(Flaky):
        data.stop_example(discard=True)


def test_is_not_flaky_on_positive_zero_and_negative_zero():
    # if we store floats in a naive way, the 0.0 and -0.0 draws will be treated
    # equivalently and will lead to flaky errors when they diverge on the boolean
    # draw.
    tree = DataTree()

    @run_to_buffer
    def buf1(data):
        data.draw_float(forced=0.0)
        # the value drawn here doesn't actually matter, since we'll force it
        # latter. we just want to avoid buffer overruns.
        data.draw_boolean()
        data.mark_interesting()

    @run_to_buffer
    def buf2(data):
        data.draw_float(forced=-0.0)
        data.draw_boolean()
        data.mark_interesting()

    data = ConjectureData.for_buffer(buf1, observer=tree.new_observer())
    f = data.draw_float()
    assert float_to_int(f) == float_to_int(0.0)
    data.draw_boolean(forced=False)
    data.freeze()

    data = ConjectureData.for_buffer(buf2, observer=tree.new_observer())
    f = data.draw_float()
    assert float_to_int(f) == float_to_int(-0.0)
    data.draw_boolean(forced=True)
    data.freeze()

    assert isinstance(tree.root.transition, Branch)
    children = tree.root.transition.children
    assert children[float_to_int(0.0)].values == [False]
    assert children[float_to_int(-0.0)].values == [True]


def test_low_probabilities_are_still_explored():
    @run_to_buffer
    def true_buf(data):
        data.draw_boolean(p=1e-10, forced=True)
        data.mark_interesting()

    @run_to_buffer
    def false_buf(data):
        data.draw_boolean(p=1e-10, forced=False)
        data.mark_interesting()

    tree = DataTree()

    data = ConjectureData.for_buffer(false_buf, observer=tree.new_observer())
    data.draw_boolean(p=1e-10)  # False

    v = tree.generate_novel_prefix(Random())
    assert v == true_buf


def _test_observed_draws_are_recorded_in_tree(ir_type):
    kwargs_strategy = {
        "integer": draw_integer_kwargs(),
        "bytes": draw_bytes_kwargs(),
        "float": draw_float_kwargs(),
        "string": draw_string_kwargs(),
        "boolean": draw_boolean_kwargs(),
    }[ir_type]

    @given(kwargs_strategy)
    def test(kwargs):
        # we currently split pseudo-choices with a single child into their
        # own transition, which clashes with our asserts below. If we ever
        # change this (say, by not writing pseudo choices to the ir at all),
        # this restriction can be relaxed.
        assume(compute_max_children(ir_type, kwargs) > 1)

        tree = DataTree()
        data = fresh_data(observer=tree.new_observer())
        draw_func = getattr(data, f"draw_{ir_type}")
        draw_func(**kwargs)

        assert tree.root.transition is None
        assert tree.root.ir_types == [ir_type]

    test()


def _test_non_observed_draws_are_not_recorded_in_tree(ir_type):
    kwargs_strategy = {
        "integer": draw_integer_kwargs(),
        "bytes": draw_bytes_kwargs(),
        "float": draw_float_kwargs(),
        "string": draw_string_kwargs(),
        "boolean": draw_boolean_kwargs(),
    }[ir_type]

    @given(kwargs_strategy)
    def test(kwargs):
        assume(compute_max_children(ir_type, kwargs) > 1)

        tree = DataTree()
        data = fresh_data(observer=tree.new_observer())
        draw_func = getattr(data, f"draw_{ir_type}")
        draw_func(**kwargs, observe=False)

        root = tree.root
        assert root.transition is None
        assert root.kwargs == root.values == root.ir_types == []

    test()


@pytest.mark.parametrize("ir_type", ["integer", "float", "boolean", "string", "bytes"])
def test_observed_ir_type_draw(ir_type):
    _test_observed_draws_are_recorded_in_tree(ir_type)


@pytest.mark.parametrize("ir_type", ["integer", "float", "boolean", "string", "bytes"])
def test_non_observed_ir_type_draw(ir_type):
    _test_non_observed_draws_are_not_recorded_in_tree(ir_type)


def test_can_generate_hard_values():
    tree = DataTree()

    min_value = 0
    max_value = 1000
    # set up `tree` such that [0, 999] have been drawn and only n=1000 remains.
    for i in range(max_value):

        @run_to_buffer
        def buf(data):
            data.draw_integer(min_value, max_value, forced=i)
            data.mark_interesting()

        data = ConjectureData.for_buffer(buf, observer=tree.new_observer())
        data.draw_integer(min_value, max_value)
        data.freeze()

    # this test doubles as conjecture coverage for using our child cache, so
    # ensure we don't miss that logic by getting lucky and drawing the correct
    # value once or twice.
    for _ in range(20):
        prefix = tree.generate_novel_prefix(Random())
        data = ConjectureData.for_buffer(prefix)
        assert data.draw_integer(min_value, max_value) == 1000


def test_can_generate_hard_floats():
    # similar to test_can_generate_hard_values, but exercises float-specific
    # logic for handling e.g. 0.0 vs -0.0 as different keys.
    tree = DataTree()

    def next_up_n(f, n):
        for _ in range(n):
            f = next_up(f)
        return f

    min_value = -0.0
    max_value = next_up_n(min_value, 100)
    for n in range(100):

        @run_to_buffer
        def buf(data):
            f = next_up_n(min_value, n)
            data.draw_float(min_value, max_value, forced=f, allow_nan=False)
            data.mark_interesting()

        data = ConjectureData.for_buffer(buf, observer=tree.new_observer())
        data.draw_float(min_value, max_value, allow_nan=False)
        data.freeze()

    # we want to leave out a single value, such that we can assert
    # generate_novel_prefix is equal to the buffer that would produce that value.
    # The problem is that floats have multiple valid buffer representations due
    # to clamping. Making the test buffer deterministic is annoying/impossible,
    # and the buffer representation is going away soon anyway, so just make
    # sure we generate the expected value (not necessarily buffer).

    # this test doubles as conjecture coverage for drawing floats from the
    # children cache. Draw a few times to ensure we hit that logic (as opposed
    # to getting lucky and drawing the correct value the first time).
    for _ in range(20):
        expected_value = next_up_n(min_value, 100)
        prefix = tree.generate_novel_prefix(Random())
        data = ConjectureData.for_buffer(prefix)
        assert data.draw_float(min_value, max_value, allow_nan=False) == expected_value


@given(draw_boolean_kwargs(), draw_integer_kwargs())
def test_datatree_repr(bool_kwargs, int_kwargs):
    tree = DataTree()

    try:
        int("not an int")
    except ValueError as e:
        origin = InterestingOrigin.from_exception(e)

    observer = tree.new_observer()
    observer.draw_boolean(True, was_forced=False, kwargs=bool_kwargs)
    observer.conclude_test(Status.INVALID, interesting_origin=None)

    observer = tree.new_observer()
    observer.draw_boolean(False, was_forced=False, kwargs=bool_kwargs)
    observer.draw_integer(42, was_forced=False, kwargs=int_kwargs)
    observer.conclude_test(Status.VALID, interesting_origin=None)

    observer = tree.new_observer()
    observer.draw_boolean(False, was_forced=False, kwargs=bool_kwargs)
    observer.draw_integer(0, was_forced=False, kwargs=int_kwargs)
    observer.draw_boolean(False, was_forced=True, kwargs=bool_kwargs)
    observer.conclude_test(Status.INTERESTING, interesting_origin=origin)

    assert (
        pretty.pretty(tree)
        == textwrap.dedent(
            f"""
        boolean True {bool_kwargs}
          Conclusion (Status.INVALID)
        boolean False {bool_kwargs}
          integer 42 {int_kwargs}
            Conclusion (Status.VALID)
          integer 0 {int_kwargs}
            boolean False [forced] {bool_kwargs}
              Conclusion (Status.INTERESTING, {origin})
        """
        ).strip()
    )


def _draw(cd, node):
    return getattr(cd, f"draw_{node.ir_type}")(**node.kwargs)


@given(st.data())
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_misaligned_nodes_after_valid_draw(data):
    # if we run a valid tree through a test function, the datatree should still
    # be able to return a Status.INVALID when a node in that tree becomes misaligned.
    tree = DataTree()
    node = data.draw(ir_nodes())

    cd = ConjectureData.for_ir_tree([node], observer=tree.new_observer())
    _draw(cd, node)
    assert cd.status is Status.VALID

    misaligned_node = data.draw(ir_nodes())
    assume(misaligned_node.ir_type != node.ir_type)

    cd = ConjectureData.for_ir_tree([misaligned_node])
    tree.simulate_test_function(cd)
    assert cd.status is Status.INVALID

    assert cd.invalid_at == (node.ir_type, node.kwargs)


@given(st.data())
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_misaligned_nodes_before_valid_draw(data):
    # if we run a misaligned tree through a test function, we should still get
    # the correct response when running the aligned version of the tree through
    # the test function afterwards.
    tree = DataTree()
    node = data.draw(ir_nodes(was_forced=False))
    misaligned_node = data.draw(ir_nodes(was_forced=False))
    assume(misaligned_node.ir_type != node.ir_type)

    cd = ConjectureData.for_ir_tree([node], observer=tree.new_observer())

    with pytest.raises(StopTest):
        _draw(cd, misaligned_node)
    cd.freeze()
    assert cd.status is Status.INVALID
    assert cd.examples.ir_tree_nodes == []

    # make sure the tree is tracking that `node` leads to Status.INVALID only
    # when trying to draw a misaligned node. If we try to draw something that
    # is valid for that node, then it's a valid draw and should lead to Status.VALID.
    cd = ConjectureData.for_ir_tree([node], observer=tree.new_observer())
    _draw(cd, node)
    cd.freeze()
    assert cd.status is Status.VALID
    assert cd.examples.ir_tree_nodes == [node]


@given(ir_nodes(was_forced=True, ir_type="float"))
def test_simulate_forced_floats(node):
    tree = DataTree()

    cd = ConjectureData.for_ir_tree([node], observer=tree.new_observer())
    cd.draw_float(**node.kwargs, forced=node.value)
    with pytest.raises(StopTest):
        cd.conclude_test(Status.VALID)

    cd = ConjectureData.for_ir_tree([node], observer=tree.new_observer())
    tree.simulate_test_function(cd)
    cd.freeze()
    assert cd.examples.ir_tree_nodes == [node]
