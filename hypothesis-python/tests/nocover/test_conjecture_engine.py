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
from hypothesis.database import InMemoryExampleDatabase, ir_from_bytes
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.internal.conjecture.shrinker import Shrinker, node_program

from tests.common.utils import counts_calls, non_covering_examples
from tests.conjecture.common import run_to_nodes, shrinking_from


def test_lot_of_dead_nodes():
    @run_to_nodes
    def nodes(data):
        for i in range(4):
            if data.draw_integer(0, 2**8 - 1) != i:
                data.mark_invalid()
        data.mark_interesting()

    assert tuple(n.value for n in nodes) == (0, 1, 2, 3)


def test_saves_data_while_shrinking(monkeypatch):
    key = b"hi there"
    n = 5
    db = InMemoryExampleDatabase()
    assert list(db.fetch(key)) == []
    seen = set()

    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.cached_test_function_ir([bytes([255] * 10)]),
    )

    def f(data):
        x = data.draw_bytes(10, 10)
        if sum(x) >= 2000 and len(seen) < n:
            seen.add(x)
        if x in seen:
            data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(database=db), database_key=key)
    runner.run()
    assert runner.interesting_examples
    assert len(seen) == n

    in_db = {ir_from_bytes(b)[0] for b in non_covering_examples(db)}
    assert in_db.issubset(seen)
    assert in_db == seen


def test_can_discard(monkeypatch):
    n = 8

    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.cached_test_function_ir(
            tuple(bytes(v) for i in range(n) for v in [i, i])
        ),
    )

    @run_to_nodes
    def nodes(data):
        seen = set()
        while len(seen) < n:
            seen.add(data.draw_bytes(1, 1))
        data.mark_interesting()

    assert len(nodes) == n


@given(st.integers(0, 255), st.integers(0, 255))
def test_cached_with_masked_byte_agrees_with_results(a, b):
    def f(data):
        data.draw_integer(0, 3)

    runner = ConjectureRunner(f)

    cached_a = runner.cached_test_function_ir([a])
    cached_b = runner.cached_test_function_ir([b])

    data_b = ConjectureData.for_choices([b], observer=runner.tree.new_observer())
    runner.test_function(data_b)

    # If the cache found an old result, then it should match the real result.
    # If it did not, then it must be because A and B were different.
    assert (cached_a is cached_b) == (cached_a.ir_nodes == data_b.ir_nodes)


def test_node_programs_fail_efficiently(monkeypatch):
    # Create 256 byte-sized nodes. None of the nodes can be deleted, and
    # every deletion attempt produces a different buffer.
    @shrinking_from(range(256))
    def shrinker(data: ConjectureData):
        values = set()
        for _ in range(256):
            v = data.draw_integer(0, 2**8 - 1)
            values.add(v)
        if len(values) == 256:
            data.mark_interesting()

    monkeypatch.setattr(
        Shrinker, "run_node_program", counts_calls(Shrinker.run_node_program)
    )
    shrinker.max_stall = 500
    shrinker.fixate_shrink_passes([node_program("XX")])

    assert shrinker.shrinks == 0
    assert 250 <= shrinker.calls <= 260
    # The node program should have been run roughly 255 times, with a little
    # bit of wiggle room for implementation details.
    #   - Too many calls mean that failing steps are doing too much work.
    #   - Too few calls mean that this test is probably miscounting and buggy.
    assert 250 <= Shrinker.run_node_program.calls <= 260
