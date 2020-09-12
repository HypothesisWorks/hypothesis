# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import re
import time
from random import Random
from unittest.mock import Mock

import pytest

from hypothesis import HealthCheck, Phase, Verbosity, settings
from hypothesis.database import ExampleDatabase, InMemoryExampleDatabase
from hypothesis.errors import FailedHealthCheck, Flaky
from hypothesis.internal.compat import int_from_bytes
from hypothesis.internal.conjecture import engine as engine_module
from hypothesis.internal.conjecture.data import ConjectureData, Overrun, Status
from hypothesis.internal.conjecture.engine import (
    MIN_TEST_CALLS,
    ConjectureRunner,
    ExitReason,
    RunIsComplete,
)
from hypothesis.internal.conjecture.pareto import DominanceRelation, dominance
from hypothesis.internal.conjecture.shrinker import Shrinker, block_program
from hypothesis.internal.conjecture.utils import integer_range
from hypothesis.internal.entropy import deterministic_PRNG
from tests.common.strategies import SLOW, HardToShrink
from tests.common.utils import no_shrink
from tests.conjecture.common import (
    SOME_LABEL,
    TEST_SETTINGS,
    buffer_size_limit,
    run_to_buffer,
    run_to_data,
    shrinking_from,
)


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

    assert x == bytes(19)


def test_deletable_draws():
    @run_to_buffer
    def x(data):
        while True:
            x = data.draw_bytes(2)
            if x[0] == 255:
                data.mark_interesting()

    assert x == bytes([255, 0])


def zero_dist(random, n):
    return bytes(n)


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
    (last_data,) = runner.interesting_examples.values()
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
        self.cached_test_function([255] * 1000)

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
    (last_data,) = runner.interesting_examples.values()
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
    assert runner.exit_reason == ExitReason.flaky
    assert count == [MIN_TEST_CALLS + 1]


def recur(i, data):
    try:
        if i >= 1:
            recur(i - 1, data)
    except RecursionError:
        data.mark_interesting()


def test_recursion_error_is_not_flaky():
    def tf(data):
        i = data.draw_bits(16)
        recur(i, data)

    runner = ConjectureRunner(tf)
    runner.run()
    assert runner.exit_reason == ExitReason.finished


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

    assert x == bytes([10]) + bytes(128 * 2)


def test_can_navigate_to_a_valid_example():
    def f(data):
        i = int_from_bytes(data.draw_bytes(2))
        data.draw_bytes(i)
        data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(max_examples=5000, database=None))
    with buffer_size_limit(2):
        runner.run()
    assert runner.interesting_examples


def test_stops_after_max_examples_when_reading():
    key = b"key"

    db = ExampleDatabase(":memory:")
    for i in range(10):
        db.save(key, bytes([i]))

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


@pytest.mark.parametrize("examples", [1, 5, 20, 50])
def test_stops_after_max_examples_when_generating_more_bugs(examples):
    seen = []
    bad = [False, False]

    def f(data):
        seen.append(data.draw_bits(32))
        # Rare, potentially multi-error conditions
        if seen[-1] > 2 ** 31:
            bad[0] = True
            raise ValueError
        bad[1] = True
        raise Exception

    runner = ConjectureRunner(
        f, settings=settings(max_examples=examples, phases=[Phase.generate])
    )
    try:
        runner.run()
    except Exception:
        pass
    # No matter what, whether examples is larger or smalller than MAX_TEST_CALLS,
    # we stop looking at max_examples.  (and re-run each failure for the traceback)
    assert len(seen) <= examples + sum(bad)


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
        seen.add(bytes(data.draw_bytes(32)))
        data.mark_interesting()

    runner = ConjectureRunner(
        f, settings=settings(database=None, phases=(Phase.reuse, Phase.generate))
    )
    runner.run()
    assert len(seen) == MIN_TEST_CALLS


def test_erratic_draws():
    n = [0]

    with pytest.raises(Flaky):

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
    with deterministic_PRNG():
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


def test_does_not_save_on_interrupt():
    def interrupts(data):
        raise KeyboardInterrupt()

    db = InMemoryExampleDatabase()

    runner = ConjectureRunner(
        interrupts, settings=settings(database=db), database_key=b"key"
    )

    with pytest.raises(KeyboardInterrupt):
        runner.run()
    assert not db.data


def test_returns_written():
    value = b"\0\1\2\3"

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
                max_examples=100, phases=no_shrink, database=None, **kwargs
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

    @run_to_data
    def data(data):
        n = data.draw_bits(4)
        b = [data.draw_bits(8) for _ in range(n)]
        if sum(b) >= target:
            data.mark_interesting()

    x = data.buffer

    assert x.count(0) == 0
    assert sum(x[1:]) == target


def test_run_nothing():
    def f(data):
        assert False

    runner = ConjectureRunner(f, settings=settings(phases=()))
    runner.run()
    assert runner.call_count == 0


class Foo:
    def __repr__(self):
        return "stuff"


def test_debug_data(capsys):
    buf = [0, 1, 2]

    def f(data):
        for x in bytes(buf):
            if data.draw_bits(8) != x:
                data.mark_invalid()
            data.start_example(1)
            data.stop_example()
        data.mark_interesting()

    runner = ConjectureRunner(
        f,
        settings=settings(
            max_examples=5000,
            database=None,
            suppress_health_check=HealthCheck.all(),
            verbosity=Verbosity.debug,
        ),
    )
    runner.cached_test_function(buf)
    runner.run()

    out, _ = capsys.readouterr()
    assert re.match("\\d+ bytes \\[.*\\] -> ", out)
    assert "INTERESTING" in out


def test_can_write_bytes_towards_the_end():
    buf = b"\1\2\3"

    def f(data):
        if data.draw_bits(1):
            data.draw_bytes(5)
            data.write(bytes(buf))
            assert bytes(data.buffer[-len(buf) :]) == buf

    with buffer_size_limit(10):
        ConjectureRunner(f).run()


def test_uniqueness_is_preserved_when_writing_at_beginning():
    seen = set()

    def f(data):
        data.write(bytes(1))
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
        self.cached_test_function(initial_attempt)

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

    for n in range(256):
        if n != 127 or not skip_target:
            db.save(runner.secondary_key, bytes([n]))
    runner.run()
    assert len(runner.interesting_examples) == 1
    for b in db.fetch(runner.secondary_key):
        assert b[0] >= 127
    assert len(list(db.fetch(runner.database_key))) == 1


def test_detects_too_small_block_starts():
    call_count = [0]

    def f(data):
        assert call_count[0] == 0
        call_count[0] += 1
        data.draw_bytes(8)
        data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(database=None))
    r = runner.cached_test_function(bytes(8))
    assert r.status == Status.INTERESTING
    assert call_count[0] == 1
    r2 = runner.cached_test_function(bytes([255] * 7))
    assert r2.status == Status.OVERRUN
    assert call_count[0] == 1


def test_shrinks_both_interesting_examples(monkeypatch):
    def generate_new_examples(self):
        self.cached_test_function(bytes([1]))

    monkeypatch.setattr(
        ConjectureRunner, "generate_new_examples", generate_new_examples
    )

    def f(data):
        n = data.draw_bits(8)
        data.mark_interesting(n & 1)

    runner = ConjectureRunner(f, database_key=b"key")
    runner.run()
    assert runner.interesting_examples[0].buffer == bytes([0])
    assert runner.interesting_examples[1].buffer == bytes([1])


def test_discarding(monkeypatch):
    monkeypatch.setattr(Shrinker, "shrink", Shrinker.remove_discarded)
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.cached_test_function(bytes([0, 1] * 10)),
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

    assert x == bytes(bytes([1]) * 10)


def test_can_remove_discarded_data():
    @shrinking_from(bytes([0] * 10 + [11]))
    def shrinker(data):
        while True:
            data.start_example(SOME_LABEL)
            b = data.draw_bits(8)
            data.stop_example(discard=(b == 0))
            if b == 11:
                break
        data.mark_interesting()

    shrinker.remove_discarded()
    assert list(shrinker.buffer) == [11]


def test_discarding_iterates_to_fixed_point():
    @shrinking_from(bytes(list(range(100, -1, -1))))
    def shrinker(data):
        data.start_example(0)
        data.draw_bits(8)
        data.stop_example(discard=True)
        while data.draw_bits(8):
            pass
        data.mark_interesting()

    shrinker.remove_discarded()
    assert list(shrinker.buffer) == [1, 0]


def test_discarding_is_not_fooled_by_empty_discards():
    @shrinking_from(bytes([1, 1]))
    def shrinker(data):
        data.draw_bits(1)
        data.start_example(0)
        data.stop_example(discard=True)
        data.draw_bits(1)
        data.mark_interesting()

    shrinker.remove_discarded()
    assert shrinker.shrink_target.has_discards


def test_discarding_can_fail(monkeypatch):
    @shrinking_from(bytes([1]))
    def shrinker(data):
        data.start_example(0)
        data.draw_bits(1)
        data.stop_example(discard=True)
        data.mark_interesting()

    shrinker.remove_discarded()
    assert any(e.discarded and e.length > 0 for e in shrinker.shrink_target.examples)


def test_shrinking_from_mostly_zero(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda self: self.cached_test_function(bytes(5) + bytes([2])),
    )

    @run_to_buffer
    def x(data):
        s = [data.draw_bits(8) for _ in range(6)]
        if any(s):
            data.mark_interesting()

    assert x == bytes(5) + bytes([1])


def test_handles_nesting_of_discard_correctly(monkeypatch):
    monkeypatch.setattr(Shrinker, "shrink", Shrinker.remove_discarded)
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.cached_test_function(bytes([0, 0, 1, 1])),
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

    assert x == bytes([1, 1])


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
            max_examples=1, database=database, suppress_health_check=HealthCheck.all()
        ),
        database_key=key,
    )

    for i in range(10):
        database.save(runner.secondary_key, bytes([i]))

    runner.cached_test_function([10])
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
            max_examples=1, database=database, suppress_health_check=HealthCheck.all()
        ),
        database_key=key,
    )

    for i in range(10):
        database.save(runner.secondary_key, bytes([i]))

    runner.cached_test_function([10])
    assert runner.interesting_examples

    assert len(set(database.fetch(key))) == 1
    assert len(set(database.fetch(runner.secondary_key))) == 10

    runner.clear_secondary_key()

    assert len(set(database.fetch(key))) == 1
    assert set(map(int_from_bytes, database.fetch(runner.secondary_key))) == set(
        range(6, 11)
    )

    (v,) = runner.interesting_examples.values()

    assert list(v.buffer) == [5]


def test_exit_because_max_iterations():
    def f(data):
        data.draw_bits(64)
        data.mark_invalid()

    runner = ConjectureRunner(
        f,
        settings=settings(
            max_examples=1, database=None, suppress_health_check=HealthCheck.all()
        ),
    )

    runner.run()

    assert runner.call_count <= 1000
    assert runner.exit_reason == ExitReason.max_iterations


def test_exit_because_shrink_phase_timeout(monkeypatch):
    val = [0]

    def fast_time():
        val[0] += 1000
        return val[0]

    def f(data):
        if data.draw_bits(64) > 2 ** 33:
            data.mark_interesting()

    monkeypatch.setattr(time, "perf_counter", fast_time)
    runner = ConjectureRunner(f, settings=settings(database=None))
    runner.run()
    assert runner.exit_reason == ExitReason.very_slow_shrinking
    assert runner.statistics["stopped-because"] == "shrinking was very slow"


def test_dependent_block_pairs_can_lower_to_zero():
    @shrinking_from([1, 0, 1])
    def shrinker(data):
        if data.draw_bits(1):
            n = data.draw_bits(16)
        else:
            n = data.draw_bits(8)

        if n == 1:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_individual_blocks"])
    assert list(shrinker.shrink_target.buffer) == [0, 1]


def test_handle_size_too_large_during_dependent_lowering():
    @shrinking_from([1, 255, 0])
    def shrinker(data):
        if data.draw_bits(1):
            data.draw_bits(16)
            data.mark_interesting()
        else:
            data.draw_bits(8)

    shrinker.fixate_shrink_passes(["minimize_individual_blocks"])


def test_block_may_grow_during_lexical_shrinking():
    initial = bytes([2, 1, 1])

    @shrinking_from(initial)
    def shrinker(data):
        n = data.draw_bits(8)
        if n == 2:
            data.draw_bits(8)
            data.draw_bits(8)
        else:
            data.draw_bits(16)
        data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_individual_blocks"])
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

    shrinker.fixate_shrink_passes([block_program("-XX")])
    assert list(shrinker.shrink_target.buffer) == [1, 7]


def test_cached_test_function_returns_right_value():
    count = [0]

    def tf(data):
        count[0] += 1
        data.draw_bits(2)
        data.mark_interesting()

    with deterministic_PRNG():
        runner = ConjectureRunner(tf, settings=TEST_SETTINGS)
        for _ in range(2):
            for b in (b"\0", b"\1"):
                d = runner.cached_test_function(b)
                assert d.status == Status.INTERESTING
                assert d.buffer == b
        assert count[0] == 2


def test_cached_test_function_does_not_reinvoke_on_prefix():
    call_count = [0]

    def test_function(data):
        call_count[0] += 1
        data.draw_bits(8)
        data.write(bytes([7]))
        data.draw_bits(8)

    with deterministic_PRNG():
        runner = ConjectureRunner(test_function, settings=TEST_SETTINGS)

        data = runner.cached_test_function(bytes(3))
        assert data.status == Status.VALID
        for n in [2, 1, 0]:
            prefix_data = runner.cached_test_function(bytes(n))
            assert prefix_data is Overrun
        assert call_count[0] == 1


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


def test_branch_ending_in_write():
    seen = set()

    def tf(data):
        count = 0
        while data.draw_bits(1):
            count += 1

        if count > 1:
            data.draw_bits(1, forced=0)

        b = bytes(data.buffer)
        assert b not in seen
        seen.add(b)

    with deterministic_PRNG():
        runner = ConjectureRunner(tf, settings=TEST_SETTINGS)

        for _ in range(100):
            prefix = runner.generate_novel_prefix()
            attempt = prefix + bytes(2)
            data = runner.cached_test_function(attempt)
            assert data.status == Status.VALID
            assert attempt.startswith(data.buffer)


def test_exhaust_space():
    with deterministic_PRNG():
        runner = ConjectureRunner(
            lambda data: data.draw_bits(1), settings=TEST_SETTINGS
        )
        runner.run()
        assert runner.tree.is_exhausted
        assert runner.valid_examples == 2


SMALL_COUNT_SETTINGS = settings(TEST_SETTINGS, max_examples=500)


def test_discards_kill_branches():
    starts = set()

    with deterministic_PRNG():

        def test(data):
            assert runner.call_count <= 256
            while True:
                data.start_example(1)
                b = data.draw_bits(8)
                data.stop_example(b != 0)
                if len(data.buffer) == 1:
                    s = bytes(data.buffer)
                    assert s not in starts
                    starts.add(s)
                if b == 0:
                    break

        runner = ConjectureRunner(test, settings=SMALL_COUNT_SETTINGS)
        runner.run()
        assert runner.call_count == 256


@pytest.mark.parametrize("n", range(1, 32))
def test_number_of_examples_in_integer_range_is_bounded(n):
    with deterministic_PRNG():

        def test(data):
            assert runner.call_count <= 2 * n
            integer_range(data, 0, n)

        runner = ConjectureRunner(test, settings=SMALL_COUNT_SETTINGS)
        runner.run()


def test_prefix_cannot_exceed_buffer_size(monkeypatch):
    buffer_size = 10
    monkeypatch.setattr(engine_module, "BUFFER_SIZE", buffer_size)

    with deterministic_PRNG():

        def test(data):
            while data.draw_bits(1):
                assert len(data.buffer) <= buffer_size
            assert len(data.buffer) <= buffer_size

        runner = ConjectureRunner(test, settings=SMALL_COUNT_SETTINGS)
        runner.run()
        assert runner.valid_examples == buffer_size


def test_does_not_shrink_multiple_bugs_when_told_not_to():
    def test(data):
        m = data.draw_bits(8)
        n = data.draw_bits(8)

        if m > 0:
            data.mark_interesting(1)
        if n > 5:
            data.mark_interesting(2)

    with deterministic_PRNG():
        runner = ConjectureRunner(
            test, settings=settings(TEST_SETTINGS, report_multiple_bugs=False)
        )
        runner.cached_test_function([255, 255])
        runner.shrink_interesting_examples()

        results = {d.buffer for d in runner.interesting_examples.values()}

    assert len(results.intersection({bytes([0, 1]), bytes([1, 0])})) == 1


def test_does_not_keep_generating_when_multiple_bugs():
    def test(data):
        if data.draw_bits(64) > 0:
            data.draw_bits(64)
            data.mark_interesting()

    with deterministic_PRNG():
        runner = ConjectureRunner(
            test,
            settings=settings(
                TEST_SETTINGS, report_multiple_bugs=False, phases=[Phase.generate]
            ),
        )

        runner.run()

    assert runner.call_count == 2


def test_shrink_after_max_examples():
    """If we find a bug, keep looking for more, and then hit the valid-example
    limit, we should still proceed to shrinking.
    """
    max_examples = 100
    fail_at = max_examples - 5

    seen = set()
    bad = set()
    post_failure_calls = [0]

    def test(data):
        if bad:
            post_failure_calls[0] += 1

        value = data.draw_bits(8)

        if value in seen and value not in bad:
            return

        seen.add(value)
        if len(seen) == fail_at:
            bad.add(value)

        if value in bad:
            data.mark_interesting()

    # This shouldn't need to be deterministic, but it makes things much easier
    # to debug if anything goes wrong.
    with deterministic_PRNG():
        runner = ConjectureRunner(
            test,
            settings=settings(
                TEST_SETTINGS,
                max_examples=max_examples,
                phases=[Phase.generate, Phase.shrink],
                report_multiple_bugs=True,
            ),
        )
        runner.shrink_interesting_examples = Mock(name="shrink_interesting_examples")

        runner.run()

    # First, verify our test assumptions: we found a bug, kept running, and
    # then hit max-examples.
    assert runner.interesting_examples
    assert post_failure_calls[0] >= (max_examples - fail_at)
    assert runner.call_count >= max_examples
    assert runner.valid_examples == max_examples

    # Now check that we still performed shrinking, even after hitting the
    # example limit.
    assert runner.shrink_interesting_examples.call_count == 1
    assert runner.exit_reason == ExitReason.finished


def test_shrink_after_max_iterations():
    """If we find a bug, keep looking for more, and then hit the test call
    limit, we should still proceed to shrinking.
    """
    max_examples = 10
    max_iterations = max_examples * 10
    fail_at = max_iterations - 5

    invalid = set()
    bad = set()
    post_failure_calls = [0]

    def test(data):
        if bad:
            post_failure_calls[0] += 1

        value = data.draw_bits(16)

        if value in invalid:
            data.mark_invalid()

        if value in bad or (not bad and len(invalid) == fail_at):
            bad.add(value)
            data.mark_interesting()

        invalid.add(value)
        data.mark_invalid()

    # This shouldn't need to be deterministic, but it makes things much easier
    # to debug if anything goes wrong.
    with deterministic_PRNG():
        runner = ConjectureRunner(
            test,
            settings=settings(
                TEST_SETTINGS,
                max_examples=max_examples,
                phases=[Phase.generate, Phase.shrink],
                report_multiple_bugs=True,
            ),
        )
        runner.shrink_interesting_examples = Mock(name="shrink_interesting_examples")

        runner.run()

    # First, verify our test assumptions: we found a bug, kept running, and
    # then hit the test call limit.
    assert runner.interesting_examples
    assert post_failure_calls[0] >= (max_iterations - fail_at) - 1
    assert runner.call_count >= max_iterations
    assert runner.valid_examples == 0

    # Now check that we still performed shrinking, even after hitting the
    # test call limit.
    assert runner.shrink_interesting_examples.call_count == 1
    assert runner.exit_reason == ExitReason.finished


def test_populates_the_pareto_front():
    with deterministic_PRNG():

        def test(data):
            data.target_observations[""] = data.draw_bits(4)

        runner = ConjectureRunner(
            test,
            settings=settings(
                max_examples=5000,
                database=InMemoryExampleDatabase(),
                suppress_health_check=HealthCheck.all(),
            ),
            database_key=b"stuff",
        )

        runner.run()

        assert len(runner.pareto_front) == 2 ** 4


def test_pareto_front_contains_smallest_valid_when_not_targeting():
    with deterministic_PRNG():

        def test(data):
            data.draw_bits(4)

        runner = ConjectureRunner(
            test,
            settings=settings(
                max_examples=5000,
                database=InMemoryExampleDatabase(),
                suppress_health_check=HealthCheck.all(),
            ),
            database_key=b"stuff",
        )

        runner.run()

        assert len(runner.pareto_front) == 1


def test_pareto_front_contains_different_interesting_reasons():
    with deterministic_PRNG():

        def test(data):
            data.mark_interesting(data.draw_bits(4))

        runner = ConjectureRunner(
            test,
            settings=settings(
                max_examples=5000,
                database=InMemoryExampleDatabase(),
                suppress_health_check=HealthCheck.all(),
            ),
            database_key=b"stuff",
        )

        runner.run()

        assert len(runner.pareto_front) == 2 ** 4


def test_database_contains_only_pareto_front():
    with deterministic_PRNG():

        def test(data):
            data.target_observations["1"] = data.draw_bits(4)
            data.draw_bits(64)
            data.target_observations["2"] = data.draw_bits(8)

        db = InMemoryExampleDatabase()

        runner = ConjectureRunner(
            test,
            settings=settings(
                max_examples=500, database=db, suppress_health_check=HealthCheck.all()
            ),
            database_key=b"stuff",
        )

        runner.run()

        assert len(runner.pareto_front) <= 500

        for v in runner.pareto_front:
            assert v.status >= Status.VALID

        assert len(db.data) == 1

        (values,) = db.data.values()
        values = set(values)

        assert len(values) == len(runner.pareto_front)

        for data in runner.pareto_front:
            assert data.buffer in values
            assert data in runner.pareto_front

        for k in values:
            assert runner.cached_test_function(k) in runner.pareto_front


def test_clears_defunct_pareto_front():
    with deterministic_PRNG():

        def test(data):
            data.draw_bits(8)
            data.draw_bits(8)

        db = InMemoryExampleDatabase()

        runner = ConjectureRunner(
            test,
            settings=settings(
                max_examples=10000,
                database=db,
                suppress_health_check=HealthCheck.all(),
                phases=[Phase.reuse],
            ),
            database_key=b"stuff",
        )

        for i in range(256):
            db.save(runner.pareto_key, bytes([i, 0]))

        runner.run()

        assert len(list(db.fetch(runner.pareto_key))) == 1


def test_replaces_all_dominated():
    def test(data):
        data.target_observations["m"] = 3 - data.draw_bits(2)
        data.target_observations["n"] = 3 - data.draw_bits(2)

    runner = ConjectureRunner(
        test,
        settings=settings(TEST_SETTINGS, database=InMemoryExampleDatabase()),
        database_key=b"stuff",
    )

    d1 = runner.cached_test_function([0, 1]).as_result()
    d2 = runner.cached_test_function([1, 0]).as_result()

    assert len(runner.pareto_front) == 2

    assert runner.pareto_front[0] == d1
    assert runner.pareto_front[1] == d2

    d3 = runner.cached_test_function([0, 0]).as_result()
    assert len(runner.pareto_front) == 1

    assert runner.pareto_front[0] == d3


def test_does_not_duplicate_elements():
    def test(data):
        data.target_observations["m"] = data.draw_bits(8)

    runner = ConjectureRunner(
        test,
        settings=settings(TEST_SETTINGS, database=InMemoryExampleDatabase()),
        database_key=b"stuff",
    )

    d1 = runner.cached_test_function([1]).as_result()

    assert len(runner.pareto_front) == 1

    # This can happen in practice if we e.g. reexecute a test because it has
    # expired from the cache. It's easier just to test it directly though
    # rather than simulate the failure mode.
    is_pareto = runner.pareto_front.add(d1)

    assert is_pareto

    assert len(runner.pareto_front) == 1


def test_includes_right_hand_side_targets_in_dominance():
    def test(data):
        if data.draw_bits(8):
            data.target_observations[""] = 10

    runner = ConjectureRunner(
        test,
        settings=settings(TEST_SETTINGS, database=InMemoryExampleDatabase()),
        database_key=b"stuff",
    )

    d1 = runner.cached_test_function([0]).as_result()
    d2 = runner.cached_test_function([1]).as_result()

    assert dominance(d1, d2) == DominanceRelation.NO_DOMINANCE


def test_smaller_interesting_dominates_larger_valid():
    def test(data):
        if data.draw_bits(8) == 0:
            data.mark_interesting()

    runner = ConjectureRunner(
        test,
        settings=settings(TEST_SETTINGS, database=InMemoryExampleDatabase()),
        database_key=b"stuff",
    )

    d1 = runner.cached_test_function([0]).as_result()
    d2 = runner.cached_test_function([1]).as_result()
    assert dominance(d1, d2) == DominanceRelation.LEFT_DOMINATES


def test_runs_full_set_of_examples():
    def test(data):
        data.draw_bits(64)

    runner = ConjectureRunner(
        test,
        settings=settings(TEST_SETTINGS, database=InMemoryExampleDatabase()),
        database_key=b"stuff",
    )

    runner.run()
    assert runner.valid_examples == TEST_SETTINGS.max_examples


def test_runs_optimisation_even_if_not_generating():
    def test(data):
        data.target_observations["n"] = data.draw_bits(16)

    with deterministic_PRNG():
        runner = ConjectureRunner(
            test, settings=settings(TEST_SETTINGS, phases=[Phase.target])
        )

        runner.cached_test_function(bytes(2))

        runner.run()

        assert runner.best_observed_targets["n"] == (2 ** 16) - 1


def test_runs_optimisation_once_when_generating():
    def test(data):
        data.target_observations["n"] = data.draw_bits(16)

    with deterministic_PRNG():
        runner = ConjectureRunner(
            test, settings=settings(TEST_SETTINGS, max_examples=100)
        )

        runner.optimise_targets = Mock(name="optimise_targets")
        try:
            runner.generate_new_examples()
        except RunIsComplete:
            pass
        assert runner.optimise_targets.call_count == 1


def test_does_not_run_optimisation_when_max_examples_is_small():
    def test(data):
        data.target_observations["n"] = data.draw_bits(16)

    with deterministic_PRNG():
        runner = ConjectureRunner(
            test, settings=settings(TEST_SETTINGS, max_examples=10)
        )

        runner.optimise_targets = Mock(name="optimise_targets")
        try:
            runner.generate_new_examples()
        except RunIsComplete:
            pass
        assert runner.optimise_targets.call_count == 0


def test_does_not_cache_extended_prefix():
    def test(data):
        data.draw_bits(64)

    with deterministic_PRNG():
        runner = ConjectureRunner(test, settings=TEST_SETTINGS)

        d1 = runner.cached_test_function(b"", extend=8)
        d2 = runner.cached_test_function(b"", extend=8)
        assert d1.status == d2.status == Status.VALID

        assert d1.buffer != d2.buffer


def test_does_cache_if_extend_is_not_used():
    calls = [0]

    def test(data):
        calls[0] += 1
        data.draw_bits(8)

    with deterministic_PRNG():
        runner = ConjectureRunner(test, settings=TEST_SETTINGS)

        d1 = runner.cached_test_function(b"\0", extend=8)
        d2 = runner.cached_test_function(b"\0", extend=8)
        assert d1.status == d2.status == Status.VALID
        assert d1.buffer == d2.buffer
        assert calls[0] == 1


def test_does_result_for_reuse():
    calls = [0]

    def test(data):
        calls[0] += 1
        data.draw_bits(8)

    with deterministic_PRNG():
        runner = ConjectureRunner(test, settings=TEST_SETTINGS)

        d1 = runner.cached_test_function(b"\0", extend=8)
        d2 = runner.cached_test_function(d1.buffer)
        assert d1.status == d2.status == Status.VALID
        assert d1.buffer == d2.buffer
        assert calls[0] == 1


def test_does_not_cache_overrun_if_extending():
    def test(data):
        data.draw_bits(64)

    with deterministic_PRNG():
        runner = ConjectureRunner(test, settings=TEST_SETTINGS)

        d1 = runner.cached_test_function(b"", extend=4)
        d2 = runner.cached_test_function(b"", extend=8)
        assert d1.status == Status.OVERRUN
        assert d2.status == Status.VALID


def test_does_cache_overrun_if_not_extending():
    def test(data):
        data.draw_bits(64)
        data.draw_bits(64)

    with deterministic_PRNG():
        runner = ConjectureRunner(test, settings=TEST_SETTINGS)

        d1 = runner.cached_test_function(bytes(8), extend=0)
        d2 = runner.cached_test_function(bytes(8), extend=8)
        assert d1.status == Status.OVERRUN
        assert d2.status == Status.VALID


def test_does_not_cache_extended_prefix_if_overrun():
    def test(data):
        data.draw_bits(64)

    with deterministic_PRNG():
        runner = ConjectureRunner(test, settings=TEST_SETTINGS)

        d1 = runner.cached_test_function(b"", extend=4)
        d2 = runner.cached_test_function(b"", extend=8)
        assert d1.status == Status.OVERRUN
        assert d2.status == Status.VALID


def test_can_be_set_to_ignore_limits():
    def test(data):
        data.draw_bits(8)

    with deterministic_PRNG():
        runner = ConjectureRunner(
            test, settings=settings(TEST_SETTINGS, max_examples=1), ignore_limits=True
        )

        for c in range(256):
            runner.cached_test_function([c])

        assert runner.tree.is_exhausted
