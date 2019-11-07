# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

from random import Random

import pytest

from hypothesis import HealthCheck, settings
from hypothesis.errors import Flaky
from hypothesis.internal.compat import hbytes, hrange
from hypothesis.internal.conjecture.data import ConjectureData, Status, StopTest
from hypothesis.internal.conjecture.datatree import DataTree
from hypothesis.internal.conjecture.engine import ConjectureRunner

TEST_SETTINGS = settings(
    max_examples=5000, database=None, suppress_health_check=HealthCheck.all()
)


def runner_for(*examples):
    if len(examples) == 1 and isinstance(examples[0], list):
        examples = examples[0]

    def accept(tf):
        runner = ConjectureRunner(tf, settings=TEST_SETTINGS, random=Random(0))
        runner.exit_with = lambda reason: None
        ran_examples = []
        for e in examples:
            e = hbytes(e)
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
        data.draw_bits(8)
        data.draw_bits(8)


def test_can_lookup_cached_examples_with_forced():
    @runner_for(b"\0\0", b"\0\1")
    def runner(data):
        data.write(b"\1")
        data.draw_bits(8)


def test_can_detect_when_tree_is_exhausted():
    @runner_for(b"\0", b"\1")
    def runner(data):
        data.draw_bits(1)

    assert runner.tree.is_exhausted


def test_can_detect_when_tree_is_exhausted_variable_size():
    @runner_for(b"\0", b"\1\0", b"\1\1")
    def runner(data):
        if data.draw_bits(1):
            data.draw_bits(1)

    assert runner.tree.is_exhausted


def test_one_dead_branch():
    @runner_for([[0, i] for i in range(16)] + [[i] for i in range(1, 16)])
    def runner(data):
        i = data.draw_bits(4)
        if i > 0:
            data.mark_invalid()
        data.draw_bits(4)

    assert runner.tree.is_exhausted


def test_non_dead_root():
    @runner_for(b"\0\0", b"\1\0", b"\1\1")
    def runner(data):
        data.draw_bits(1)
        data.draw_bits(1)


def test_can_reexecute_dead_examples():
    @runner_for(b"\0\0", b"\0\1", b"\0\0")
    def runner(data):
        data.draw_bits(1)
        data.draw_bits(1)


def test_novel_prefixes_are_novel():
    def tf(data):
        for _ in range(4):
            data.write(b"\0")
            data.draw_bits(2)

    runner = ConjectureRunner(tf, settings=TEST_SETTINGS, random=Random(0))
    for _ in range(100):
        prefix = runner.tree.generate_novel_prefix(runner.random)
        example = prefix + hbytes(8 - len(prefix))
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
        lambda data: [data.draw_bits(1) for _ in range(2)],
        settings=TEST_SETTINGS,
        random=Random(0),
    )
    runner.cached_test_function(b"\0\0")
    assert runner.tree.rewrite(b"\0")[1] == Status.OVERRUN


def test_stores_the_tree_flat_until_needed():
    @runner_for(hbytes(10))
    def runner(data):
        for _ in hrange(10):
            data.draw_bits(1)
        data.mark_interesting()

    root = runner.tree.root
    assert len(root.bit_lengths) == 10
    assert len(root.values) == 10
    assert root.transition.status == Status.INTERESTING


def test_split_in_the_middle():
    @runner_for([0, 0, 2], [0, 1, 3])
    def runner(data):
        data.draw_bits(1)
        data.draw_bits(1)
        data.draw_bits(4)
        data.mark_interesting()

    root = runner.tree.root
    assert len(root.bit_lengths) == len(root.values) == 1
    assert list(root.transition.children[0].values) == [2]
    assert list(root.transition.children[1].values) == [3]


def test_stores_forced_nodes():
    @runner_for(hbytes(3))
    def runner(data):
        data.draw_bits(1, forced=0)
        data.draw_bits(1)
        data.draw_bits(1, forced=0)
        data.mark_interesting()

    root = runner.tree.root
    assert root.forced == {0, 2}


def test_correctly_relocates_forced_nodes():
    @runner_for([0, 0], [1, 0])
    def runner(data):
        data.draw_bits(1)
        data.draw_bits(1, forced=0)
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
    data.draw_bits(1)
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"", observer=tree.new_observer())
    with pytest.raises(Flaky):
        data.conclude_test(Status.INVALID)


def test_concluding_with_overrun_at_prefix_is_not_flaky():
    tree = DataTree()
    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    data.draw_bits(1)
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"", observer=tree.new_observer())
    with pytest.raises(StopTest):
        data.conclude_test(Status.OVERRUN)


def test_changing_n_bits_is_flaky_in_prefix():
    tree = DataTree()
    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    data.draw_bits(1)
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    with pytest.raises(Flaky):
        data.draw_bits(2)


def test_changing_n_bits_is_flaky_in_branch():
    tree = DataTree()

    for i in [0, 1]:
        data = ConjectureData.for_buffer([i], observer=tree.new_observer())
        data.draw_bits(1)
        with pytest.raises(StopTest):
            data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    with pytest.raises(Flaky):
        data.draw_bits(2)


def test_extending_past_conclusion_is_flaky():
    tree = DataTree()
    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    data.draw_bits(1)
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"\1\0", observer=tree.new_observer())
    data.draw_bits(1)

    with pytest.raises(Flaky):
        data.draw_bits(1)


def test_changing_to_forced_is_flaky():
    tree = DataTree()
    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    data.draw_bits(1)
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"\1\0", observer=tree.new_observer())

    with pytest.raises(Flaky):
        data.draw_bits(1, forced=0)


def test_changing_value_of_forced_is_flaky():
    tree = DataTree()
    data = ConjectureData.for_buffer(b"\1", observer=tree.new_observer())
    data.draw_bits(1, forced=1)
    with pytest.raises(StopTest):
        data.conclude_test(Status.INTERESTING)

    data = ConjectureData.for_buffer(b"\1\0", observer=tree.new_observer())

    with pytest.raises(Flaky):
        data.draw_bits(1, forced=0)


def test_does_not_truncate_if_unseen():
    tree = DataTree()
    b = hbytes([1, 2, 3, 4])
    assert tree.rewrite(b) == (b, None)


def test_truncates_if_seen():
    tree = DataTree()

    b = hbytes([1, 2, 3, 4])

    data = ConjectureData.for_buffer(b, observer=tree.new_observer())
    data.draw_bits(8)
    data.draw_bits(8)
    data.freeze()

    assert tree.rewrite(b) == (b[:2], Status.VALID)


def test_child_becomes_exhausted_after_split():
    tree = DataTree()
    data = ConjectureData.for_buffer([0, 0], observer=tree.new_observer())
    data.draw_bits(8)
    data.draw_bits(8, forced=0)
    data.freeze()

    data = ConjectureData.for_buffer([1, 0], observer=tree.new_observer())
    data.draw_bits(8)
    data.draw_bits(8)
    data.freeze()

    assert not tree.is_exhausted
    assert tree.root.transition.children[0].is_exhausted


def test_will_generate_novel_prefix_to_avoid_exhausted_branches():
    tree = DataTree()
    data = ConjectureData.for_buffer([1], observer=tree.new_observer())
    data.draw_bits(1)
    data.freeze()

    data = ConjectureData.for_buffer([0, 1], observer=tree.new_observer())
    data.draw_bits(1)
    data.draw_bits(8)
    data.freeze()

    prefix = list(tree.generate_novel_prefix(Random(0)))

    assert len(prefix) == 2
    assert prefix[0] == 0


def test_will_mark_changes_in_discard_as_flaky():
    tree = DataTree()
    data = ConjectureData.for_buffer([1, 1], observer=tree.new_observer())
    data.start_example(10)
    data.draw_bits(1)
    data.stop_example()
    data.draw_bits(1)
    data.freeze()

    data = ConjectureData.for_buffer([1, 1], observer=tree.new_observer())
    data.start_example(10)
    data.draw_bits(1)

    with pytest.raises(Flaky):
        data.stop_example(discard=True)
