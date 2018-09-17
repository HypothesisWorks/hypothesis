# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

from __future__ import division, print_function, absolute_import

from random import Random

import pytest

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from tests.common.utils import no_shrink, non_covering_examples
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.internal.compat import hbytes, hrange, int_from_bytes
from tests.cover.test_conjecture_engine import run_to_buffer, \
    shrink_to_data
from hypothesis.internal.conjecture.data import Status, ConjectureData
from hypothesis.internal.conjecture.engine import RunIsComplete, \
    ConjectureRunner


def test_lot_of_dead_nodes():
    @run_to_buffer
    def x(data):
        for i in range(4):
            if data.draw_bytes(1)[0] != i:
                data.mark_invalid()
        data.mark_interesting()
    assert x == hbytes([0, 1, 2, 3])


def test_saves_data_while_shrinking(monkeypatch):
    key = b'hi there'
    n = 5
    db = InMemoryExampleDatabase()
    assert list(db.fetch(key)) == []
    seen = set()

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([255] * 10)))

    def f(data):
        x = data.draw_bytes(10)
        if sum(x) >= 2000 and len(seen) < n:
            seen.add(hbytes(x))
        if hbytes(x) in seen:
            data.mark_interesting()
    runner = ConjectureRunner(
        f, settings=settings(database=db), database_key=key)
    runner.run()
    assert runner.interesting_examples
    assert len(seen) == n
    in_db = non_covering_examples(db)
    assert in_db.issubset(seen)
    assert in_db == seen


@given(st.randoms(), st.random_module())
@settings(
    phases=no_shrink, deadline=None,
    suppress_health_check=[HealthCheck.hung_test]
)
def test_maliciously_bad_generator(rnd, seed):
    @run_to_buffer
    def x(data):
        for _ in range(rnd.randint(1, 100)):
            data.draw_bytes(rnd.randint(1, 10))
        if rnd.randint(0, 1):
            data.mark_invalid()
        else:
            data.mark_interesting()


def test_can_discard(monkeypatch):
    n = 8

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([
                v for i in range(n) for v in [i, i]
            ])))

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
        f, settings=settings(database=None, max_examples=256, buffer_size=2),
        random=Random(0),
    )
    with pytest.raises(RunIsComplete):
        runner.cached_test_function(b'')
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
        data.write(hbytes(b'\x01\x02'))
        data.write(hbytes(b'\x01\x00'))
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

    @shrink_to_data(buffer=[235, 0, 0, 255])
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

    assert f.buffer == hbytes([10, 0, 0, 30])


@given(st.integers(0, 255), st.integers(0, 255))
def test_prescreen_with_masked_byte_agrees_with_results(byte_a, byte_b):
    def f(data):
        data.draw_bits(2)

    runner = ConjectureRunner(f)

    data_a = ConjectureData.for_buffer(hbytes([byte_a]))
    data_b = ConjectureData.for_buffer(hbytes([byte_b]))

    runner.test_function(data_a)
    prescreen_b = runner.prescreen_buffer(hbytes([byte_b]))
    # Always test buffer B, to check whether the prescreen was correct.
    runner.test_function(data_b)

    # If the prescreen passed, then the buffers should be different.
    # If it failed, then the buffers should be the same.
    assert prescreen_b == (data_a.buffer != data_b.buffer)


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
