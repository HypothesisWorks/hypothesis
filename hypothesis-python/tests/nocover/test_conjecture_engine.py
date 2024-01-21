# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given, settings, strategies as st
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.internal.compat import int_from_bytes
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.internal.conjecture.shrinker import Shrinker, block_program

from tests.common.utils import counts_calls, non_covering_examples
from tests.conjecture.common import run_to_buffer, shrinking_from


def test_lot_of_dead_nodes():
    @run_to_buffer
    def x(data):
        for i in range(4):
            if data.draw_bytes(1)[0] != i:
                data.mark_invalid()
        data.mark_interesting()

    assert x == bytes([0, 1, 2, 3])


def test_saves_data_while_shrinking(monkeypatch):
    key = b"hi there"
    n = 5
    db = InMemoryExampleDatabase()
    assert list(db.fetch(key)) == []
    seen = set()

    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.cached_test_function([255] * 10),
    )

    def f(data):
        x = data.draw_bytes(10)
        if sum(x) >= 2000 and len(seen) < n:
            seen.add(x)
        if x in seen:
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
        lambda runner: runner.cached_test_function(
            [v for i in range(n) for v in [i, i]]
        ),
    )

    @run_to_buffer
    def x(data):
        seen = set()
        while len(seen) < n:
            seen.add(bytes(data.draw_bytes(1)))
        data.mark_interesting()

    assert len(x) == n


def test_regression_1():
    # This is a really hard to reproduce bug that previously triggered a very
    # specific exception inside one of the shrink passes. It's unclear how
    # useful this regression test really is, but nothing else caught the
    # problem.
    #
    # update 2024-01-15: we've since changed generation and are about to
    # change shrinking, so it's unclear if the failure case this test was aimed
    # at (1) is still being covered or (2) even exists anymore.
    # we can probably safely remove this once the shrinker is rebuilt.
    @run_to_buffer
    def x(data):
        data.draw_bytes(2, forced=b"\x01\x02")
        data.draw_bytes(2, forced=b"\x01\x00")
        v = data.draw_integer(0, 2**41 - 1)
        if v >= 512 or v == 254:
            data.mark_interesting()

    assert list(x)[:-2] == [1, 2, 1, 0, 0, 0, 0, 0]

    assert int_from_bytes(x[-2:]) in (254, 512)


@given(st.integers(0, 255), st.integers(0, 255))
def test_cached_with_masked_byte_agrees_with_results(byte_a, byte_b):
    def f(data):
        data.draw_integer(0, 3)

    runner = ConjectureRunner(f)

    cached_a = runner.cached_test_function(bytes([byte_a]))
    cached_b = runner.cached_test_function(bytes([byte_b]))

    data_b = ConjectureData.for_buffer(
        bytes([byte_b]), observer=runner.tree.new_observer()
    )
    runner.test_function(data_b)

    # If the cache found an old result, then it should match the real result.
    # If it did not, then it must be because A and B were different.
    assert (cached_a is cached_b) == (cached_a.buffer == data_b.buffer)


def test_block_programs_fail_efficiently(monkeypatch):
    # Create 256 byte-sized blocks. None of the blocks can be deleted, and
    # every deletion attempt produces a different buffer.
    @shrinking_from(bytes(range(256)))
    def shrinker(data):
        values = set()
        for _ in range(256):
            v = data.draw_integer(0, 2**8 - 1)
            values.add(v)
        if len(values) == 256:
            data.mark_interesting()

    monkeypatch.setattr(
        Shrinker, "run_block_program", counts_calls(Shrinker.run_block_program)
    )

    shrinker.max_stall = 500

    shrinker.fixate_shrink_passes([block_program("XX")])

    assert shrinker.shrinks == 0
    assert 250 <= shrinker.calls <= 260

    # The block program should have been run roughly 255 times, with a little
    # bit of wiggle room for implementation details.
    #   - Too many calls mean that failing steps are doing too much work.
    #   - Too few calls mean that this test is probably miscounting and buggy.
    assert 250 <= Shrinker.run_block_program.calls <= 260
