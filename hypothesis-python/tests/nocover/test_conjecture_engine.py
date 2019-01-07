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
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

from random import Random

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.internal.compat import hbytes, hrange, int_from_bytes
from hypothesis.internal.conjecture.data import ConjectureData, Status
from hypothesis.internal.conjecture.engine import ConjectureRunner, RunIsComplete
from tests.common.utils import non_covering_examples
from tests.cover.test_conjecture_engine import run_to_buffer, shrink, shrinking_from


def test_lot_of_dead_nodes():
    @run_to_buffer
    def x(data):
        for i in range(4):
            if data.draw_bytes(1)[0] != i:
                data.mark_invalid()
        data.mark_interesting()

    assert x == hbytes([0, 1, 2, 3])


def test_saves_data_while_shrinking(monkeypatch):
    key = b"hi there"
    n = 5
    db = InMemoryExampleDatabase()
    assert list(db.fetch(key)) == []
    seen = set()

    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.test_function(ConjectureData.for_buffer([255] * 10)),
    )

    def f(data):
        x = data.draw_bytes(10)
        if sum(x) >= 2000 and len(seen) < n:
            seen.add(hbytes(x))
        if hbytes(x) in seen:
            data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(database=db), database_key=key)
    runner.run()
    assert runner.interesting_examples
    assert len(seen) == n
    in_db = non_covering_examples(db)
    assert in_db.issubset(seen)
    assert in_db == seen


def test_can_discard(monkeypatch):
    n = 8

    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([v for i in range(n) for v in [i, i]])
        ),
    )

    @run_to_buffer
    def x(data):
        seen = set()
        while len(seen) < n:
            seen.add(hbytes(data.draw_bytes(1)))
        data.mark_interesting()

    assert len(x) == n


def test_exhaustive_enumeration_of_partial_buffer():
    seen = set()

    def f(data):
        k = data.draw_bytes(2)
        assert k[1] == 0
        assert k not in seen
        seen.add(k)

    seen_prefixes = set()

    runner = ConjectureRunner(
        f,
        settings=settings(database=None, max_examples=256, buffer_size=2),
        random=Random(0),
    )
    with pytest.raises(RunIsComplete):
        runner.cached_test_function(b"")
        for _ in hrange(256):
            p = runner.generate_novel_prefix()
            assert p not in seen_prefixes
            seen_prefixes.add(p)
            data = ConjectureData.for_buffer(hbytes(p + hbytes(2)))
            runner.test_function(data)
            assert data.status == Status.VALID
            node = 0
            for b in data.buffer:
                node = runner.tree[node][b]
            assert node in runner.dead
    assert len(seen) == 256


def test_regression_1():
    # This is a really hard to reproduce bug that previously triggered a very
    # specific exception inside one of the shrink passes. It's unclear how
    # useful this regression test really is, but nothing else caught the
    # problem.
    @run_to_buffer
    def x(data):
        data.write(hbytes(b"\x01\x02"))
        data.write(hbytes(b"\x01\x00"))
        v = data.draw_bits(41)
        if v >= 512 or v == 254:
            data.mark_interesting()

    assert list(x)[:-2] == [1, 2, 1, 0, 0, 0, 0, 0]

    assert int_from_bytes(x[-2:]) in (254, 512)


def test_shrink_offset_pairs_handles_block_structure_change():
    """Regression test for a rare error in ``shrink_offset_pairs``.

    This test should run without raising an ``IndexError`` in the
    shrinker.
    """

    @shrink([235, 0, 0, 255], "shrink_offset_pairs")
    def f(data):
        x = data.draw_bytes(1)[0]

        # Change the block structure in response to a shrink improvement,
        # to trigger the bug.
        if x == 10:
            data.draw_bytes(1)
            data.draw_bytes(1)
        else:
            data.draw_bytes(2)

        y = data.draw_bytes(1)[0]

        # Require the target blocks to be non-trivial and have a fixed
        # difference, so that the intended shrinker pass is used.
        if x >= 10 and y - x == 20:
            data.mark_interesting()

    assert f == [10, 0, 0, 30]


def test_retaining_sum_considers_zero_destination_blocks():
    """Explicitly test that this shrink pass will try to move data into blocks
    that are currently all-zero."""

    @shrink([100, 0, 0], "minimize_block_pairs_retaining_sum")
    def f(data):
        x = data.draw_bytes(1)[0]
        data.draw_bytes(1)
        y = data.draw_bytes(1)[0]

        if x >= 10 and (x + y) == 100:
            data.mark_interesting()

    assert f == [10, 0, 90]


@given(st.integers(0, 255), st.integers(0, 255))
def test_cached_with_masked_byte_agrees_with_results(byte_a, byte_b):
    def f(data):
        data.draw_bits(2)

    runner = ConjectureRunner(f)

    cached_a = runner.cached_test_function(hbytes([byte_a]))
    cached_b = runner.cached_test_function(hbytes([byte_b]))

    data_b = ConjectureData.for_buffer(hbytes([byte_b]))
    runner.test_function(data_b)

    # If the cache found an old result, then it should match the real result.
    # If it did not, then it must be because A and B were different.
    assert (cached_a is cached_b) == (cached_a.buffer == data_b.buffer)


def test_each_pair_of_blocks():
    initial = hbytes([1, 1, 1])

    @shrinking_from(initial)
    def shrinker(data):
        data.draw_bits(1)
        data.draw_bits(1)
        data.draw_bits(1)
        data.mark_interesting()

    bounds = [
        (a.bounds, b.bounds)
        for a, b in shrinker.each_pair_of_blocks(lambda block: True, lambda block: True)
    ]

    assert bounds == [((0, 1), (1, 2)), ((0, 1), (2, 3)), ((1, 2), (2, 3))]


def test_each_pair_of_blocks_with_filters():
    initial = hbytes(5)

    @shrinking_from(initial)
    def shrinker(data):
        for x in range(5):
            data.draw_bits(1)
        data.mark_interesting()

    blocks = [
        (a.index, b.index)
        for a, b in shrinker.each_pair_of_blocks(
            lambda block: block.index != 1, lambda block: block.index != 3
        )
    ]

    assert blocks == [(0, 1), (0, 2), (0, 4), (2, 4), (3, 4)]


def test_each_pair_of_blocks_handles_change():
    initial = hbytes([9] + [0] * 10)

    @shrinking_from(initial)
    def shrinker(data):
        x = data.draw_bits(8)
        for y in range(x):
            data.draw_bits(1)
        data.mark_interesting()

    blocks = []
    for a, b in shrinker.each_pair_of_blocks(lambda block: True, lambda block: True):
        if a.index == 0 and b.index == 6:
            shrinker.incorporate_new_buffer(hbytes([3] + [0] * 10))
        blocks.append((a.index, b.index))

    assert blocks == [
        (0, 1),
        (0, 2),
        (0, 3),
        (0, 4),
        (0, 5),
        (0, 6),
        (1, 2),
        (1, 3),
        (2, 3),
    ]
