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

import itertools
import re
from random import Random, seed as seed_random

import attr
import pytest

import hypothesis.internal.conjecture.engine as engine_module
import hypothesis.internal.conjecture.floats as flt
from hypothesis import HealthCheck, Phase, Verbosity, settings
from hypothesis.database import ExampleDatabase, InMemoryExampleDatabase
from hypothesis.errors import FailedHealthCheck
from hypothesis.internal.compat import hbytes, hrange, int_from_bytes, int_to_bytes
from hypothesis.internal.conjecture.data import (
    MAX_DEPTH,
    ConjectureData,
    Overrun,
    Status,
)
from hypothesis.internal.conjecture.engine import (
    ConjectureRunner,
    ExitReason,
    RunIsComplete,
    TargetSelector,
    sort_key,
)
from hypothesis.internal.conjecture.shrinker import (
    PassClassification,
    Shrinker,
    block_program,
)
from hypothesis.internal.conjecture.shrinking import Float
from hypothesis.internal.conjecture.utils import Sampler, calc_label_from_name
from hypothesis.internal.entropy import deterministic_PRNG
from tests.common.strategies import SLOW, HardToShrink
from tests.common.utils import no_shrink

SOME_LABEL = calc_label_from_name("some label")


TEST_SETTINGS = settings(
    max_examples=5000,
    buffer_size=1024,
    database=None,
    suppress_health_check=HealthCheck.all(),
)


def run_to_buffer(f):
    with deterministic_PRNG():
        runner = ConjectureRunner(f, settings=TEST_SETTINGS)
        runner.run()
        assert runner.interesting_examples
        last_data, = runner.interesting_examples.values()
        return hbytes(last_data.buffer)


def test_can_index_results():
    @run_to_buffer
    def f(data):
        data.draw_bytes(5)
        data.mark_interesting()

    assert f.index(0) == 0
    assert f.count(0) == 5


def test_non_cloneable_intervals():
    @run_to_buffer
    def x(data):
        data.draw_bytes(10)
        data.draw_bytes(9)
        data.mark_interesting()

    assert x == hbytes(19)


def test_duplicate_buffers():
    @run_to_buffer
    def x(data):
        t = data.draw_bytes(10)
        if not any(t):
            data.mark_invalid()
        s = data.draw_bytes(10)
        if s == t:
            data.mark_interesting()

    assert x == hbytes([0] * 9 + [1]) * 2


def test_deletable_draws():
    @run_to_buffer
    def x(data):
        while True:
            x = data.draw_bytes(2)
            if x[0] == 255:
                data.mark_interesting()

    assert x == hbytes([255, 0])


def zero_dist(random, n):
    return hbytes(n)


def test_can_load_data_from_a_corpus():
    key = b"hi there"
    db = ExampleDatabase()
    value = b"=\xc3\xe4l\x81\xe1\xc2H\xc9\xfb\x1a\xb6bM\xa8\x7f"
    db.save(key, value)

    def f(data):
        if data.draw_bytes(len(value)) == value:
            data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(database=db), database_key=key)
    runner.run()
    last_data, = runner.interesting_examples.values()
    assert last_data.buffer == value
    assert len(list(db.fetch(key))) == 1


def slow_shrinker():
    strat = HardToShrink()

    def accept(data):
        if data.draw(strat):
            data.mark_interesting()

    return accept


@pytest.mark.parametrize("n", [1, 5])
def test_terminates_shrinks(n, monkeypatch):
    from hypothesis.internal.conjecture import engine

    db = InMemoryExampleDatabase()

    def generate_new_examples(self):
        def draw_bytes(data, n):
            return hbytes([255] * n)

        self.test_function(
            ConjectureData(draw_bytes=draw_bytes, max_length=self.settings.buffer_size)
        )

    monkeypatch.setattr(
        ConjectureRunner, "generate_new_examples", generate_new_examples
    )
    monkeypatch.setattr(engine, "MAX_SHRINKS", n)

    runner = ConjectureRunner(
        slow_shrinker(),
        settings=settings(max_examples=5000, database=db),
        random=Random(0),
        database_key=b"key",
    )
    runner.run()
    last_data, = runner.interesting_examples.values()
    assert last_data.status == Status.INTERESTING
    assert runner.shrinks == n
    in_db = set(db.data[runner.secondary_key])
    assert len(in_db) == n


def test_detects_flakiness():
    failed_once = [False]
    count = [0]

    def tf(data):
        data.draw_bytes(1)
        count[0] += 1
        if not failed_once[0]:
            failed_once[0] = True
            data.mark_interesting()

    runner = ConjectureRunner(tf)
    runner.run()
    assert count == [2]


def test_variadic_draw():
    def draw_list(data):
        result = []
        while True:
            data.start_example(SOME_LABEL)
            d = data.draw_bytes(1)[0] & 7
            if d:
                result.append(data.draw_bytes(d))
            data.stop_example()
            if not d:
                break
        return result

    @run_to_buffer
    def b(data):
        if any(all(d) for d in draw_list(data)):
            data.mark_interesting()

    ls = draw_list(ConjectureData.for_buffer(b))
    assert len(ls) == 1
    assert len(ls[0]) == 1


def test_draw_to_overrun():
    @run_to_buffer
    def x(data):
        d = (data.draw_bytes(1)[0] - 8) & 0xFF
        data.draw_bytes(128 * d)
        if d >= 2:
            data.mark_interesting()

    assert x == hbytes([10]) + hbytes(128 * 2)


def test_can_navigate_to_a_valid_example():
    def f(data):
        i = int_from_bytes(data.draw_bytes(2))
        data.draw_bytes(i)
        data.mark_interesting()

    runner = ConjectureRunner(
        f, settings=settings(max_examples=5000, buffer_size=2, database=None)
    )
    runner.run()
    assert runner.interesting_examples


def test_stops_after_max_examples_when_reading():
    key = b"key"

    db = ExampleDatabase(":memory:")
    for i in range(10):
        db.save(key, hbytes([i]))

    seen = []

    def f(data):
        seen.append(data.draw_bytes(1))

    runner = ConjectureRunner(
        f, settings=settings(max_examples=1, database=db), database_key=key
    )
    runner.run()
    assert len(seen) == 1


def test_stops_after_max_examples_when_generating():
    seen = []

    def f(data):
        seen.append(data.draw_bytes(1))

    runner = ConjectureRunner(f, settings=settings(max_examples=1, database=None))
    runner.run()
    assert len(seen) == 1


def test_interleaving_engines():
    children = []

    @run_to_buffer
    def x(data):
        rnd = Random(data.draw_bytes(1))

        def g(d2):
            d2.draw_bytes(1)
            data.mark_interesting()

        runner = ConjectureRunner(g, random=rnd)
        children.append(runner)
        runner.run()
        if runner.interesting_examples:
            data.mark_interesting()

    assert x == b"\0"
    for c in children:
        assert not c.interesting_examples


def test_phases_can_disable_shrinking():
    seen = set()

    def f(data):
        seen.add(hbytes(data.draw_bytes(32)))
        data.mark_interesting()

    runner = ConjectureRunner(
        f, settings=settings(database=None, phases=(Phase.reuse, Phase.generate))
    )
    runner.run()
    assert len(seen) == 1


def test_erratic_draws():
    n = [0]

    @run_to_buffer
    def x(data):
        data.draw_bytes(n[0])
        data.draw_bytes(255 - n[0])
        if n[0] == 255:
            data.mark_interesting()
        else:
            n[0] += 1


def test_no_read_no_shrink():
    count = [0]

    @run_to_buffer
    def x(data):
        count[0] += 1
        data.mark_interesting()

    assert x == b""
    assert count == [1]


def test_one_dead_branch():
    seed_random(0)
    seen = set()

    @run_to_buffer
    def x(data):
        i = data.draw_bytes(1)[0]
        if i > 0:
            data.mark_invalid()
        i = data.draw_bytes(1)[0]
        if len(seen) < 255:
            seen.add(i)
        elif i not in seen:
            data.mark_interesting()


def test_fully_exhaust_base(monkeypatch):
    """In this test we generate all possible values for the first byte but
    never get to the point where we exhaust the root of the tree."""
    seed_random(0)

    seen = set()

    def f(data):
        key = (data.draw_bits(2), data.draw_bits(2))
        assert key not in seen
        seen.add(key)

    runner = ConjectureRunner(
        f,
        settings=settings(
            max_examples=10000, phases=no_shrink, buffer_size=1024, database=None
        ),
    )

    for c in hrange(4):
        runner.cached_test_function([0, c])

    assert 1 in runner.tree.dead

    runner.run()


def test_saves_on_interrupt():
    def interrupts(data):
        raise KeyboardInterrupt()

    db = InMemoryExampleDatabase()

    runner = ConjectureRunner(
        interrupts, settings=settings(database=db), database_key=b"key"
    )

    with pytest.raises(KeyboardInterrupt):
        runner.run()
    assert db.data


def test_returns_written():
    value = hbytes(b"\0\1\2\3")

    @run_to_buffer
    def written(data):
        data.write(value)
        data.mark_interesting()

    assert value == written


def fails_health_check(label, **kwargs):
    def accept(f):
        runner = ConjectureRunner(
            f,
            settings=settings(
                max_examples=100,
                phases=no_shrink,
                buffer_size=1024,
                database=None,
                **kwargs
            ),
        )

        with pytest.raises(FailedHealthCheck) as e:
            runner.run()
        assert e.value.health_check == label
        assert not runner.interesting_examples

    return accept


def test_fails_health_check_for_all_invalid():
    @fails_health_check(HealthCheck.filter_too_much)
    def _(data):
        data.draw_bytes(2)
        data.mark_invalid()


def test_fails_health_check_for_large_base():
    @fails_health_check(HealthCheck.large_base_example)
    def _(data):
        data.draw_bytes(10 ** 6)


def test_fails_health_check_for_large_non_base():
    @fails_health_check(HealthCheck.data_too_large)
    def _(data):
        if data.draw_bits(8):
            data.draw_bytes(10 ** 6)


def test_fails_health_check_for_slow_draws():
    @fails_health_check(HealthCheck.too_slow)
    def _(data):
        data.draw(SLOW)


@pytest.mark.parametrize("n_large", [1, 5, 8, 15])
def test_can_shrink_variable_draws(n_large):
    target = 128 * n_large

    @run_to_buffer
    def x(data):
        n = data.draw_bits(4)
        b = [data.draw_bits(8) for _ in hrange(n)]
        if sum(b) >= target:
            data.mark_interesting()

    assert x.count(0) == 0
    assert sum(x[1:]) == target


@pytest.mark.parametrize("n", [1, 5, 8, 15])
def test_can_shrink_variable_draws_with_just_deletion(n, monkeypatch):
    @shrinking_from([n] + [0] * (n - 1) + [1])
    def shrinker(data):
        n = data.draw_bits(4)
        b = [data.draw_bits(8) for _ in hrange(n)]
        if any(b):
            data.mark_interesting()

    # We normally would have populated this in minimize_individual_blocks
    shrinker.is_shrinking_block = lambda x: True

    fixate(Shrinker.example_deletion_with_block_lowering)(shrinker)

    assert list(shrinker.shrink_target.buffer) == [1, 1]


def test_deletion_and_lowering_fails_to_shrink(monkeypatch):
    monkeypatch.setattr(
        Shrinker, "shrink", Shrinker.example_deletion_with_block_lowering
    )
    # Would normally be added by minimize_individual_blocks, but we skip
    # that phase in this test.
    monkeypatch.setattr(Shrinker, "is_shrinking_block", lambda self, i: i == 0)

    def gen(self):
        data = ConjectureData.for_buffer(hbytes(10))
        self.test_function(data)

    monkeypatch.setattr(ConjectureRunner, "generate_new_examples", gen)

    @run_to_buffer
    def x(data):
        for _ in hrange(10):
            data.draw_bytes(1)
        data.mark_interesting()

    assert x == hbytes(10)


def test_run_nothing():
    def f(data):
        assert False

    runner = ConjectureRunner(f, settings=settings(phases=()))
    runner.run()
    assert runner.call_count == 0


class Foo(object):
    def __repr__(self):
        return "stuff"


@pytest.mark.parametrize("event", ["hi", Foo()])
def test_note_events(event):
    def f(data):
        data.note_event(event)
        data.draw_bytes(1)

    runner = ConjectureRunner(f)
    runner.run()
    assert runner.event_call_counts[str(event)] == runner.call_count > 0


def test_debug_data(capsys):
    buf = [0, 1, 2]

    def f(data):
        for x in hbytes(buf):
            if data.draw_bits(8) != x:
                data.mark_invalid()
            data.start_example(1)
            data.stop_example()
        data.mark_interesting()

    runner = ConjectureRunner(
        f,
        settings=settings(
            max_examples=5000,
            buffer_size=1024,
            database=None,
            suppress_health_check=HealthCheck.all(),
            verbosity=Verbosity.debug,
        ),
    )
    runner.test_function(ConjectureData.for_buffer(buf))
    runner.run()

    out, _ = capsys.readouterr()
    assert re.match(u"\\d+ bytes \\[.*\\] -> ", out)
    assert "INTERESTING" in out
    assert "[]" not in out


def test_zeroes_bytes_above_bound():
    def f(data):
        if data.draw_bits(1):
            x = data.draw_bytes(9)
            assert not any(x[4:8])

    ConjectureRunner(f, settings=settings(buffer_size=10)).run()


def test_can_write_bytes_towards_the_end():
    buf = b"\1\2\3"

    def f(data):
        if data.draw_bits(1):
            data.draw_bytes(5)
            data.write(hbytes(buf))
            assert hbytes(data.buffer[-len(buf) :]) == buf

    ConjectureRunner(f, settings=settings(buffer_size=10)).run()


def test_can_increase_number_of_bytes_drawn_in_tail():
    # This is designed to trigger a case where the zero bound queue will end up
    # increasing the size of data drawn because moving zeroes into the initial
    # prefix will increase the amount drawn.
    def f(data):
        x = data.draw_bytes(5)
        n = x.count(0)
        b = data.draw_bytes(n + 1)
        assert not any(b)

    runner = ConjectureRunner(
        f,
        settings=settings(
            max_examples=100, buffer_size=11, suppress_health_check=HealthCheck.all()
        ),
    )

    runner.run()


def test_uniqueness_is_preserved_when_writing_at_beginning():
    seen = set()

    def f(data):
        data.write(hbytes(1))
        n = data.draw_bits(3)
        assert n not in seen
        seen.add(n)

    runner = ConjectureRunner(f, settings=settings(max_examples=50))
    runner.run()
    assert runner.valid_examples == len(seen)


@pytest.mark.parametrize("skip_target", [False, True])
@pytest.mark.parametrize("initial_attempt", [127, 128])
def test_clears_out_its_database_on_shrinking(
    initial_attempt, skip_target, monkeypatch
):
    def generate_new_examples(self):
        self.test_function(ConjectureData.for_buffer(hbytes([initial_attempt])))

    monkeypatch.setattr(
        ConjectureRunner, "generate_new_examples", generate_new_examples
    )

    key = b"key"
    db = InMemoryExampleDatabase()

    def f(data):
        if data.draw_bits(8) >= 127:
            data.mark_interesting()

    runner = ConjectureRunner(
        f,
        settings=settings(database=db, max_examples=256),
        database_key=key,
        random=Random(0),
    )

    for n in hrange(256):
        if n != 127 or not skip_target:
            db.save(runner.secondary_key, hbytes([n]))
    runner.run()
    assert len(runner.interesting_examples) == 1
    for b in db.fetch(runner.secondary_key):
        assert b[0] >= 127
    assert len(list(db.fetch(runner.database_key))) == 1


def test_can_delete_intervals(monkeypatch):
    def generate_new_examples(self):
        self.test_function(ConjectureData.for_buffer(hbytes([255] * 10 + [1, 3])))

    monkeypatch.setattr(
        ConjectureRunner, "generate_new_examples", generate_new_examples
    )
    monkeypatch.setattr(Shrinker, "shrink", fixate(Shrinker.adaptive_example_deletion))

    def f(data):
        while True:
            n = data.draw_bits(8)
            if n == 255:
                continue
            elif n == 1:
                break
            else:
                data.mark_invalid()
        if data.draw_bits(8) == 3:
            data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(database=None))
    runner.run()
    x, = runner.interesting_examples.values()
    assert x.buffer == hbytes([1, 3])


def test_detects_too_small_block_starts():
    call_count = [0]

    def f(data):
        assert call_count[0] == 0
        call_count[0] += 1
        data.draw_bytes(8)
        data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(database=None))
    r = ConjectureData.for_buffer(hbytes(8))
    runner.test_function(r)
    assert r.status == Status.INTERESTING
    assert call_count[0] == 1
    r2 = runner.cached_test_function(hbytes([255] * 7))
    assert r2.status == Status.OVERRUN
    assert call_count[0] == 1


def test_shrinks_both_interesting_examples(monkeypatch):
    def generate_new_examples(self):
        self.test_function(ConjectureData.for_buffer(hbytes([1])))

    monkeypatch.setattr(
        ConjectureRunner, "generate_new_examples", generate_new_examples
    )

    def f(data):
        n = data.draw_bits(8)
        data.mark_interesting(n & 1)

    runner = ConjectureRunner(f, database_key=b"key")
    runner.run()
    assert runner.interesting_examples[0].buffer == hbytes([0])
    assert runner.interesting_examples[1].buffer == hbytes([1])


def test_duplicate_blocks_that_go_away(monkeypatch):
    monkeypatch.setattr(Shrinker, "shrink", Shrinker.minimize_duplicated_blocks)
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(hbytes([1, 1, 1, 2] * 2 + [5] * 2))
        ),
    )

    @run_to_buffer
    def x(data):
        x = data.draw_bits(32)
        y = data.draw_bits(32)
        if x != y:
            data.mark_invalid()
        b = [data.draw_bytes(1) for _ in hrange(x & 255)]
        if len(set(b)) <= 1:
            data.mark_interesting()

    assert x == hbytes([0] * 8)


def test_accidental_duplication(monkeypatch):
    @shrinking_from([18] * 20)
    def shrinker(data):
        x = data.draw_bits(8)
        y = data.draw_bits(8)
        if x != y:
            data.mark_invalid()
        if x < 5:
            data.mark_invalid()
        b = [data.draw_bytes(1) for _ in hrange(x)]
        if len(set(b)) == 1:
            data.mark_interesting()

    shrinker.clear_passes()
    shrinker.add_new_pass("minimize_duplicated_blocks")
    shrinker.shrink()
    assert list(shrinker.buffer) == [5] * 7


def test_discarding(monkeypatch):
    monkeypatch.setattr(Shrinker, "shrink", Shrinker.remove_discarded)
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(hbytes([0, 1] * 10))
        ),
    )

    @run_to_buffer
    def x(data):
        count = 0
        while count < 10:
            data.start_example(SOME_LABEL)
            b = data.draw_bits(1)
            if b:
                count += 1
            data.stop_example(discard=not b)
        data.mark_interesting()

    assert x == hbytes(hbytes([1]) * 10)


def fixate(f):
    def accept(self):
        prev = None
        while self.shrink_target is not prev:
            prev = self.shrink_target
            f(self)

    return accept


def test_can_remove_discarded_data():
    @shrinking_from(hbytes([0] * 10) + hbytes([11]))
    def shrinker(data):
        while True:
            data.start_example(SOME_LABEL)
            b = data.draw_bits(8)
            data.stop_example(discard=(b == 0))
            if b == 11:
                break
        data.mark_interesting()

    shrinker.run_shrink_pass("remove_discarded")
    assert list(shrinker.buffer) == [11]


def test_discarding_iterates_to_fixed_point():
    @shrinking_from(hbytes([1] * 10) + hbytes([0]))
    def shrinker(data):
        data.start_example(0)
        data.draw_bits(1)
        data.stop_example(discard=True)
        while data.draw_bits(1):
            pass
        data.mark_interesting()

    shrinker.run_shrink_pass("remove_discarded")
    assert list(shrinker.buffer) == [1, 0]


def shrink_pass(name):
    def run(self):
        self.run_shrink_pass(name)

    return run


def test_discarding_can_fail(monkeypatch):
    @shrinking_from(hbytes([1]))
    def shrinker(data):
        data.start_example(0)
        data.draw_bits(1)
        data.stop_example(discard=True)
        data.mark_interesting()

    shrinker.remove_discarded()
    assert shrinker.shrink_target.has_discards


@pytest.mark.parametrize("bits", [3, 9])
@pytest.mark.parametrize("prefix", [b"", b"\0"])
@pytest.mark.parametrize("seed", [0])
def test_exhaustive_enumeration(prefix, bits, seed):
    seen = set()

    def f(data):
        if prefix:
            data.write(hbytes(prefix))
            assert len(data.buffer) == len(prefix)
        k = data.draw_bits(bits)
        assert k not in seen
        seen.add(k)

    size = 2 ** bits

    seen_prefixes = set()

    runner = ConjectureRunner(
        f, settings=settings(database=None, max_examples=size), random=Random(seed)
    )
    with pytest.raises(RunIsComplete):
        runner.cached_test_function(b"")
        for _ in hrange(size):
            p = runner.generate_novel_prefix()
            assert p not in seen_prefixes
            seen_prefixes.add(p)
            data = ConjectureData.for_buffer(hbytes(p + hbytes(2 + len(prefix))))
            runner.test_function(data)
            assert data.status == Status.VALID
            node = 0
            for b in data.buffer:
                node = runner.tree.nodes[node][b]
            assert node in runner.tree.dead
    assert len(seen) == size


def test_depth_bounds_in_generation():
    depth = [0]

    def tails(data, n):
        depth[0] = max(depth[0], n)
        if data.draw_bits(8):
            data.start_example(SOME_LABEL)
            tails(data, n + 1)
            data.stop_example()

    def f(data):
        tails(data, 0)

    runner = ConjectureRunner(f, settings=settings(database=None, max_examples=20))
    runner.run()
    assert 0 < depth[0] <= MAX_DEPTH


def test_shrinking_from_mostly_zero(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda self: self.cached_test_function(hbytes(5) + hbytes([2])),
    )

    @run_to_buffer
    def x(data):
        s = [data.draw_bits(8) for _ in hrange(6)]
        if any(s):
            data.mark_interesting()

    assert x == hbytes(5) + hbytes([1])


def test_handles_nesting_of_discard_correctly(monkeypatch):
    monkeypatch.setattr(Shrinker, "shrink", Shrinker.remove_discarded)
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(hbytes([0, 0, 1, 1]))
        ),
    )

    @run_to_buffer
    def x(data):
        while True:
            data.start_example(SOME_LABEL)
            succeeded = data.draw_bits(1)
            data.start_example(SOME_LABEL)
            data.draw_bits(1)
            data.stop_example(discard=not succeeded)
            data.stop_example(discard=not succeeded)
            if succeeded:
                data.mark_interesting()

    assert x == hbytes([1, 1])


def test_can_zero_subintervals(monkeypatch):
    @shrinking_from(hbytes([3, 0, 0, 0, 1]) * 10)
    def shrinker(data):
        for _ in hrange(10):
            data.start_example(SOME_LABEL)
            n = data.draw_bits(8)
            data.draw_bytes(n)
            data.stop_example()
            if data.draw_bits(8) != 1:
                return
        data.mark_interesting()

    shrinker.run_shrink_pass("zero_examples")
    assert list(shrinker.buffer) == [0, 1] * 10


def test_can_pass_to_an_indirect_descendant(monkeypatch):
    initial = hbytes([1, 10, 0, 0, 1, 0, 0, 10, 0, 0])

    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.cached_test_function(initial),
    )

    monkeypatch.setattr(Shrinker, "shrink", Shrinker.pass_to_descendant)

    def tree(data):
        data.start_example(1)
        n = data.draw_bits(1)
        label = data.draw_bits(8)
        if n:
            tree(data)
            tree(data)
        data.stop_example(1)
        return label

    @run_to_buffer
    def x(data):
        if tree(data) == 10:
            data.mark_interesting()

    assert list(x) == [0, 10]


def shrink(buffer, *passes):
    def accept(f):
        shrinker = shrinking_from(buffer)(f)

        prev = None
        while shrinker.shrink_target is not prev:
            prev = shrinker.shrink_target
            for p in passes:
                shrinker.run_shrink_pass(p)
        return list(shrinker.buffer)

    return accept


def test_shrinking_blocks_from_common_offset(monkeypatch):
    monkeypatch.setattr(
        Shrinker,
        "shrink",
        lambda self: (
            # Run minimize_individual_blocks twice so we have both blocks show
            # as changed regardless of which order this happens in.
            self.minimize_individual_blocks(),
            self.minimize_individual_blocks(),
            self.lower_common_block_offset(),
        ),
    )

    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.test_function(ConjectureData.for_buffer([11, 10])),
    )

    @run_to_buffer
    def x(data):
        m = data.draw_bits(8)
        n = data.draw_bits(8)
        if abs(m - n) <= 1 and max(m, n) > 0:
            data.mark_interesting()

    assert sorted(x) == [0, 1]


def test_handle_empty_draws(monkeypatch):
    monkeypatch.setattr(Shrinker, "shrink", Shrinker.adaptive_example_deletion)

    lambda runner: runner.test_function(ConjectureData.for_buffer([1, 1, 0]))

    @run_to_buffer
    def x(data):
        while True:
            data.start_example(SOME_LABEL)
            n = data.draw_bits(1)
            data.start_example(SOME_LABEL)
            data.stop_example()
            data.stop_example(discard=n > 0)
            if not n:
                break
        data.mark_interesting()

    assert x == hbytes([0])


def test_large_initial_write():
    big = hbytes(b"\xff") * 512

    def f(data):
        data.write(big)
        data.draw_bits(63)

    with deterministic_PRNG():
        runner = ConjectureRunner(
            f,
            settings=settings(
                max_examples=5000,
                buffer_size=1024,
                database=None,
                suppress_health_check=HealthCheck.all(),
            ),
        )
        runner.run()

    assert runner.exit_reason == ExitReason.finished


def test_can_reorder_examples(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([1, 0, 1, 1, 0, 1, 0, 0, 0])
        ),
    )

    monkeypatch.setattr(Shrinker, "shrink", Shrinker.reorder_examples)

    @run_to_buffer
    def x(data):
        total = 0
        for _ in range(5):
            data.start_example(0)
            if data.draw_bits(8):
                total += data.draw_bits(9)
            data.stop_example(0)
        if total == 2:
            data.mark_interesting()

    assert list(x) == [0, 0, 0, 1, 0, 1, 1, 0, 1]


def test_permits_but_ignores_raising_order(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.test_function(ConjectureData.for_buffer([1])),
    )

    monkeypatch.setattr(
        Shrinker, "shrink", lambda self: self.incorporate_new_buffer(hbytes([2]))
    )

    @run_to_buffer
    def x(data):
        data.draw_bits(2)
        data.mark_interesting()

    assert list(x) == [1]


def test_block_deletion_can_delete_short_ranges(monkeypatch):
    @shrinking_from([v for i in range(5) for _ in range(i + 1) for v in [0, i]])
    def shrinker(data):
        while True:
            n = data.draw_bits(16)
            for _ in range(n):
                if data.draw_bits(16) != n:
                    data.mark_invalid()
            if n == 4:
                data.mark_interesting()

    for i in range(1, 5):
        block_program("X" * i)(shrinker)
    assert list(shrinker.shrink_target.buffer) == [0, 4] * 5


def test_try_shrinking_blocks_ignores_overrun_blocks(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.test_function(ConjectureData.for_buffer([3, 3, 0, 1])),
    )

    monkeypatch.setattr(
        Shrinker,
        "shrink",
        lambda self: self.try_shrinking_blocks((0, 1, 5), hbytes([2])),
    )

    @run_to_buffer
    def x(data):
        n1 = data.draw_bits(8)
        data.draw_bits(8)
        if n1 == 3:
            data.draw_bits(8)
        k = data.draw_bits(8)
        if k == 1:
            data.mark_interesting()

    assert list(x) == [2, 2, 1]


def shrinking_from(start):
    def accept(f):
        with deterministic_PRNG():
            runner = ConjectureRunner(
                f,
                settings=settings(
                    max_examples=5000,
                    buffer_size=1024,
                    database=None,
                    suppress_health_check=HealthCheck.all(),
                ),
            )
            runner.test_function(ConjectureData.for_buffer(start))
            assert runner.interesting_examples
            last_data, = runner.interesting_examples.values()
            return runner.new_shrinker(
                last_data, lambda d: d.status == Status.INTERESTING
            )

    return accept


def test_dependent_block_pairs_is_up_to_shrinking_integers():
    # Unit test extracted from a failure in tests/nocover/test_integers.py
    distribution = Sampler([4.0, 8.0, 1.0, 1.0, 0.5])

    sizes = [8, 16, 32, 64, 128]

    @shrinking_from(b"\x03\x01\x00\x00\x00\x00\x00\x01\x00\x02\x01")
    def shrinker(data):
        size = sizes[distribution.sample(data)]
        result = data.draw_bits(size)
        sign = (-1) ** (result & 1)
        result = (result >> 1) * sign
        cap = data.draw_bits(8)

        if result >= 32768 and cap == 1:
            data.mark_interesting()

    shrinker.minimize_individual_blocks()
    assert list(shrinker.shrink_target.buffer) == [1, 1, 0, 1, 0, 0, 1]


def test_finding_a_minimal_balanced_binary_tree():
    # Tests iteration while the shape of the thing being iterated over can
    # change. In particular the current example can go from trivial to non
    # trivial.

    def tree(data):
        # Returns height of a binary tree and whether it is height balanced.
        data.start_example("tree")
        n = data.draw_bits(1)
        if n == 0:
            result = (1, True)
        else:
            h1, b1 = tree(data)
            h2, b2 = tree(data)
            result = (1 + max(h1, h2), b1 and b2 and abs(h1 - h2) <= 1)
        data.stop_example("tree")
        return result

    # Starting from an unbalanced tree of depth six
    @shrinking_from([1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
    def shrinker(data):
        _, b = tree(data)
        if not b:
            data.mark_interesting()

    shrinker.adaptive_example_deletion()
    shrinker.reorder_examples()

    assert list(shrinker.shrink_target.buffer) == [1, 0, 1, 0, 1, 0, 0]


def test_database_clears_secondary_key():
    key = b"key"
    database = InMemoryExampleDatabase()

    def f(data):
        if data.draw_bits(8) == 10:
            data.mark_interesting()
        else:
            data.mark_invalid()

    runner = ConjectureRunner(
        f,
        settings=settings(
            max_examples=1,
            buffer_size=1024,
            database=database,
            suppress_health_check=HealthCheck.all(),
        ),
        database_key=key,
    )

    for i in range(10):
        database.save(runner.secondary_key, hbytes([i]))

    runner.test_function(ConjectureData.for_buffer(hbytes([10])))
    assert runner.interesting_examples

    assert len(set(database.fetch(key))) == 1
    assert len(set(database.fetch(runner.secondary_key))) == 10

    runner.clear_secondary_key()

    assert len(set(database.fetch(key))) == 1
    assert len(set(database.fetch(runner.secondary_key))) == 0


def test_database_uses_values_from_secondary_key():
    key = b"key"
    database = InMemoryExampleDatabase()

    def f(data):
        if data.draw_bits(8) >= 5:
            data.mark_interesting()
        else:
            data.mark_invalid()

    runner = ConjectureRunner(
        f,
        settings=settings(
            max_examples=1,
            buffer_size=1024,
            database=database,
            suppress_health_check=HealthCheck.all(),
        ),
        database_key=key,
    )

    for i in range(10):
        database.save(runner.secondary_key, hbytes([i]))

    runner.test_function(ConjectureData.for_buffer(hbytes([10])))
    assert runner.interesting_examples

    assert len(set(database.fetch(key))) == 1
    assert len(set(database.fetch(runner.secondary_key))) == 10

    runner.clear_secondary_key()

    assert len(set(database.fetch(key))) == 1
    assert set(map(int_from_bytes, database.fetch(runner.secondary_key))) == set(
        range(6, 11)
    )

    v, = runner.interesting_examples.values()

    assert list(v.buffer) == [5]


def test_exit_because_max_iterations():
    def f(data):
        data.draw_bits(64)
        data.mark_invalid()

    runner = ConjectureRunner(
        f,
        settings=settings(
            max_examples=1,
            buffer_size=1024,
            database=None,
            suppress_health_check=HealthCheck.all(),
        ),
    )

    runner.run()

    assert runner.call_count <= 1000
    assert runner.exit_reason == ExitReason.max_iterations


def test_dependent_block_pairs_can_lower_to_zero():
    @shrinking_from([1, 0, 1])
    def shrinker(data):
        if data.draw_bits(1):
            n = data.draw_bits(16)
        else:
            n = data.draw_bits(8)

        if n == 1:
            data.mark_interesting()

    shrinker.minimize_individual_blocks()
    assert list(shrinker.shrink_target.buffer) == [0, 1]


def test_handle_size_too_large_during_dependent_lowering():
    @shrinking_from([1, 255, 0])
    def shrinker(data):
        if data.draw_bits(1):
            data.draw_bits(16)
            data.mark_interesting()
        else:
            data.draw_bits(8)

    shrinker.minimize_individual_blocks()


def test_zero_examples_will_zero_blocks():
    @shrinking_from([1, 1, 1])
    def shrinker(data):
        n = data.draw_bits(1)
        data.draw_bits(1)
        m = data.draw_bits(1)
        if n == m == 1:
            data.mark_interesting()

    shrinker.run_shrink_pass("zero_examples")
    assert list(shrinker.shrink_target.buffer) == [1, 0, 1]


def test_non_trivial_examples():
    initial = hbytes([1, 0, 1])

    @shrinking_from(initial)
    def shrinker(data):
        data.draw_bits(1)
        data.draw_bits(1)
        data.draw_bits(1)
        data.mark_interesting()

    assert {(ex.start, ex.end) for ex in shrinker.each_non_trivial_example()} == {
        (0, 3),
        (0, 1),
        (2, 3),
    }


def test_become_trivial_during_shrinking():
    @shrinking_from([1, 1, 1])
    def shrinker(data):
        data.draw_bits(1)
        data.draw_bits(1)
        data.draw_bits(1)
        data.mark_interesting()

    for ex in shrinker.each_non_trivial_example():
        assert ex.length == 3
        shrinker.incorporate_new_buffer(hbytes(3))


def test_continues_iterating_if_an_example_becomes_trivial():
    @shrinking_from([1, 1, 1])
    def shrinker(data):
        data.draw_bits(1)
        data.draw_bits(1)
        data.draw_bits(1)
        data.mark_interesting()

    endpoints = set()
    for ex in shrinker.each_non_trivial_example():
        endpoints.add((ex.start, ex.end))
        if ex.start == 1:
            shrinker.incorporate_new_buffer([1, 0, 1])
    assert endpoints == {(0, 3), (0, 1), (1, 2), (2, 3)}


def test_each_non_trivial_example_includes_each_non_trivial_example():
    @shrinking_from([1, 0, 1])
    def shrinker(data):
        data.draw_bits(1)
        data.draw_bits(1)
        data.draw_bits(1)
        data.mark_interesting()

    endpoints = {(ex.start, ex.end) for ex in shrinker.each_non_trivial_example()}

    assert endpoints == {(0, 3), (0, 1), (2, 3)}


def test_non_trivial_examples_boundaries_can_change():
    initial = hbytes([2, 1, 1])

    @shrinking_from(initial)
    def shrinker(data):
        n = data.draw_bits(8)
        if n == 2:
            data.draw_bits(8)
            data.draw_bits(8)
        else:
            data.draw_bits(16)
        data.mark_interesting()

    it = shrinker.each_non_trivial_example()
    assert next(it).length == 3
    shrinker.incorporate_new_buffer([1, 1, 1])
    assert next(it).length == 2
    assert next(it).length == 1


def test_block_may_grow_during_lexical_shrinking():
    initial = hbytes([2, 1, 1])

    @shrinking_from(initial)
    def shrinker(data):
        n = data.draw_bits(8)
        if n == 2:
            data.draw_bits(8)
            data.draw_bits(8)
        else:
            data.draw_bits(16)
        data.mark_interesting()

    shrinker.minimize_individual_blocks()
    assert list(shrinker.shrink_target.buffer) == [0, 0, 0]


def test_lower_common_block_offset_does_nothing_when_changed_blocks_are_zero():
    @shrinking_from([1, 0, 1, 0])
    def shrinker(data):
        data.draw_bits(1)
        data.draw_bits(1)
        data.draw_bits(1)
        data.draw_bits(1)
        data.mark_interesting()

    shrinker.mark_changed(1)
    shrinker.mark_changed(3)
    shrinker.lower_common_block_offset()
    assert list(shrinker.shrink_target.buffer) == [1, 0, 1, 0]


def test_lower_common_block_offset_ignores_zeros():
    @shrinking_from([2, 2, 0])
    def shrinker(data):
        n = data.draw_bits(8)
        data.draw_bits(8)
        data.draw_bits(8)
        if n > 0:
            data.mark_interesting()

    for i in range(3):
        shrinker.mark_changed(i)
    shrinker.lower_common_block_offset()
    assert list(shrinker.shrink_target.buffer) == [1, 1, 0]


def test_pandas_hack():
    @shrinking_from([2, 1, 1, 7])
    def shrinker(data):
        n = data.draw_bits(8)
        m = data.draw_bits(8)
        if n == 1:
            if m == 7:
                data.mark_interesting()
        data.draw_bits(8)
        if data.draw_bits(8) == 7:
            data.mark_interesting()

    shrinker.run_shrink_pass("block_program('-XX')")
    assert list(shrinker.shrink_target.buffer) == [1, 7]


def test_passes_can_come_back_to_life():
    initial = hbytes([1, 2, 3, 4, 5, 6])
    buf1 = hbytes([0, 1, 3, 4, 5, 6])
    buf2 = hbytes([0, 1, 3, 4, 4, 6])

    good = {initial, buf1, buf2}

    @shrinking_from(initial)
    def shrinker(data):
        string = hbytes([data.draw_bits(8) for _ in range(6)])
        if string in good:
            data.mark_interesting()

    shrinker.clear_passes()
    shrinker.add_new_pass(block_program("--"))
    shrinker.add_new_pass(block_program("-"))

    shrinker.single_greedy_shrink_iteration()
    assert shrinker.shrink_target.buffer == buf1

    shrinker.single_greedy_shrink_iteration()
    assert shrinker.shrink_target.buffer == buf2


def test_will_enable_previously_bad_passes_when_failing_to_shrink():
    # We lead the shrinker down the garden path a bit where it keeps making
    # progress but only lexically. When it finally gets down to the minimum
    good = {
        hbytes([1, 2, 3, 4, 5, 6]),
        hbytes([1, 2, 3, 4, 5, 5]),
        hbytes([1, 2, 2, 4, 5, 5]),
        hbytes([1, 2, 2, 4, 4, 5]),
        hbytes([0, 2, 2, 4, 4, 5]),
        hbytes([0, 1, 2, 4, 4, 5]),
    }

    initial = max(good)
    final = min(good)

    @shrinking_from(initial + hbytes([0, 7]))
    def shrinker(data):
        string = hbytes([data.draw_bits(8) for _ in range(6)])
        if string in good:
            n = 0
            while data.draw_bits(8) != 7:
                n += 1
            if not (string == final or n > 0):
                data.mark_invalid()
            data.mark_interesting()

    # In order to get to the minimized result we want to run both of these,
    # but the second pass starts out as disabled (and anyway won't work until
    # the first has hit fixity).
    shrinker.clear_passes()
    shrinker.add_new_pass(block_program("-"))
    shrinker.add_new_pass(block_program("X"))

    shrinker.shrink()

    assert shrinker.shrink_target.buffer == final + hbytes([7])


def test_shrink_passes_behave_sensibly_with_standard_operators():
    @shrinking_from(hbytes([1]))
    def shrinker(data):
        if data.draw_bits(1):
            data.mark_interesting()

    passes = shrinker.passes

    lookup = {p: p for p in passes}
    for p in passes:
        assert lookup[p] is p

    for p, q in itertools.combinations(passes, 2):
        assert p < q
        assert p != q


def test_shrink_pass_may_go_from_solid_to_dubious():

    initial = hbytes([10])

    @shrinking_from(initial)
    def shrinker(data):
        n = data.draw_bits(8)
        if n >= 9:
            data.mark_interesting()

    sp = shrinker.shrink_pass("minimize_individual_blocks")
    assert sp.classification == PassClassification.CANDIDATE
    shrinker.run_shrink_pass(sp)
    assert sp.classification == PassClassification.HOPEFUL
    shrinker.run_shrink_pass(sp)
    assert sp.classification == PassClassification.DUBIOUS


def test_runs_adaptive_delete_on_first_pass_if_discarding_does_not_work():
    @shrinking_from([0, 1])
    def shrinker(data):
        while not data.draw_bits(1):
            pass
        data.mark_interesting()

    shrinker.single_greedy_shrink_iteration()
    assert list(shrinker.buffer) == [1]


def test_alphabet_minimization():
    @shrink(hbytes((10, 11)) * 5, "alphabet_minimize")
    def x(data):
        buf = data.draw_bytes(10)
        if len(set(buf)) > 2:
            data.mark_invalid()
        if buf[0] < buf[1] and buf[1] > 1:
            data.mark_interesting()

    assert x == [0, 2] * 5


def test_keeps_using_solid_passes_while_they_shrink_size():
    good = {
        hbytes([0, 1, 2, 3, 4, 5]),
        hbytes([0, 1, 2, 3, 5]),
        hbytes([0, 1, 3, 5]),
        hbytes([1, 3, 5]),
        hbytes([1, 5]),
    }
    initial = max(good, key=sort_key)

    @shrinking_from(initial)
    def shrinker(data):
        while True:
            data.draw_bits(8)
            if hbytes(data.buffer) in good:
                data.mark_interesting()

    shrinker.clear_passes()

    d1 = shrinker.add_new_pass(block_program("X"))
    d2 = shrinker.add_new_pass(block_program("-"))

    for _ in range(3):
        shrinker.single_greedy_shrink_iteration()
        assert d1.classification == PassClassification.HOPEFUL
        assert d2.classification == PassClassification.CANDIDATE


fake_data_counter = 0


@attr.s()
class FakeData(object):
    status = attr.ib(default=Status.VALID)
    global_identifer = attr.ib(init=False)

    def __attrs_post_init__(self):
        global fake_data_counter
        fake_data_counter += 1
        self.global_identifier = fake_data_counter


def test_target_selector_will_maintain_a_bounded_pool():
    selector = TargetSelector(random=Random(0), pool_size=3)

    for i in range(100):
        selector.add(FakeData())
        assert len(selector) == min(i + 1, 3)


def test_target_selector_will_use_novel_examples_preferentially():
    selector = TargetSelector(random=Random(0), pool_size=3)
    seen = set()

    for i in range(100):
        selector.add(FakeData())
        assert len(selector) == min(i + 1, 3)
        t = selector.select().global_identifier
        assert t not in seen
        seen.add(t)


def test_target_selector_will_eventually_reuse_examples():
    selector = TargetSelector(random=Random(0), pool_size=2)
    seen = set()

    selector.add(FakeData())
    selector.add(FakeData())

    for _ in range(2):
        x = selector.select()
        assert x.global_identifier not in seen
        seen.add(x.global_identifier)

    for _ in range(2):
        x = selector.select()
        assert x.global_identifier in seen


def test_cached_test_function_does_not_reinvoke_on_prefix():
    call_count = [0]

    def test_function(data):
        call_count[0] += 1
        data.draw_bits(8)
        data.write(hbytes([7]))
        data.draw_bits(8)

    with deterministic_PRNG():
        runner = ConjectureRunner(test_function, settings=TEST_SETTINGS)

        data = runner.cached_test_function(hbytes(3))
        assert data.status == Status.VALID
        for n in [2, 1, 0]:
            prefix_data = runner.cached_test_function(hbytes(n))
            assert prefix_data is Overrun
        assert call_count[0] == 1


def test_float_shrink_can_run_when_canonicalisation_does_not_work(monkeypatch):
    # This should be an error when called
    monkeypatch.setattr(Float, "shrink", None)

    base_buf = int_to_bytes(flt.base_float_to_lex(1000.0), 8) + hbytes(1)

    @shrinking_from(base_buf)
    def shrinker(data):
        flt.draw_float(data)
        if hbytes(data.buffer) == base_buf:
            data.mark_interesting()

    shrinker.minimize_floats()

    assert shrinker.shrink_target.buffer == base_buf


def test_will_evict_entries_from_the_cache(monkeypatch):
    monkeypatch.setattr(engine_module, "CACHE_SIZE", 5)
    count = [0]

    def tf(data):
        data.draw_bytes(1)
        count[0] += 1

    runner = ConjectureRunner(tf, settings=TEST_SETTINGS)

    for _ in range(3):
        for n in range(10):
            runner.cached_test_function([n])

    # Because we exceeded the cache size, our previous
    # calls will have been evicted, so each call to
    # cached_test_function will have to reexecute.
    assert count[0] == 30
