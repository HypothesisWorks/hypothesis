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

from hypothesis import HealthCheck, settings
from hypothesis.internal.compat import hbytes
from hypothesis.internal.conjecture.data import ConjectureData, Status
from hypothesis.internal.conjecture.engine import ConjectureRunner, RunIsComplete

TEST_SETTINGS = settings(
    max_examples=5000, database=None, suppress_health_check=HealthCheck.all()
)


def runner_for(*examples):
    if len(examples) == 1 and isinstance(examples[0], list):
        examples = examples[0]

    def accept(tf):
        runner = ConjectureRunner(tf, settings=TEST_SETTINGS, random=Random(0))
        ran_examples = []
        for e in examples:
            e = hbytes(e)
            data = ConjectureData.for_buffer(e)
            try:
                runner.test_function(data)
            except RunIsComplete:
                pass
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
