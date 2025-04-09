# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import enum
import re
import time
from random import Random
from unittest.mock import Mock

import pytest

from hypothesis import (
    HealthCheck,
    Phase,
    Verbosity,
    assume,
    given,
    settings,
    strategies as st,
)
from hypothesis.database import (
    InMemoryExampleDatabase,
    choices_from_bytes,
    choices_to_bytes,
)
from hypothesis.errors import FailedHealthCheck, FlakyStrategyDefinition
from hypothesis.internal.compat import PYPY, bit_count, int_from_bytes
from hypothesis.internal.conjecture import engine as engine_module
from hypothesis.internal.conjecture.data import ConjectureData, Overrun, Status
from hypothesis.internal.conjecture.datatree import compute_max_children
from hypothesis.internal.conjecture.engine import (
    MIN_TEST_CALLS,
    ConjectureRunner,
    ExitReason,
    HealthCheckState,
    RunIsComplete,
)
from hypothesis.internal.conjecture.junkdrawer import startswith
from hypothesis.internal.conjecture.pareto import DominanceRelation, dominance
from hypothesis.internal.conjecture.shrinker import Shrinker
from hypothesis.internal.entropy import deterministic_PRNG

from tests.common.debug import minimal
from tests.common.strategies import SLOW, HardToShrink
from tests.common.utils import no_shrink
from tests.conjecture.common import (
    SOME_LABEL,
    TEST_SETTINGS,
    buffer_size_limit,
    interesting_origin,
    nodes,
    run_to_nodes,
    shrinking_from,
)


def test_non_cloneable_intervals():
    @run_to_nodes
    def nodes(data):
        data.draw_bytes(10, 10)
        data.draw_bytes(9, 9)
        data.mark_interesting()

    assert tuple(n.value for n in nodes) == (bytes(10), bytes(9))


def test_deletable_draws():
    @run_to_nodes
    def nodes(data):
        while True:
            x = data.draw_bytes(2, 2)
            if x[0] == 255:
                data.mark_interesting()

    assert tuple(n.value for n in nodes) == (b"\xff\x00",)


def test_can_load_data_from_a_corpus():
    key = b"hi there"
    db = InMemoryExampleDatabase()
    value = b"=\xc3\xe4l\x81\xe1\xc2H\xc9\xfb\x1a\xb6bM\xa8\x7f"
    db.save(key, choices_to_bytes([value]))

    def f(data):
        if data.draw_bytes() == value:
            data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(database=db), database_key=key)
    runner.run()
    (last_data,) = runner.interesting_examples.values()
    assert last_data.choices == (value,)
    assert len(list(db.fetch(key))) == 1


def slow_shrinker():
    strat = HardToShrink()

    def accept(data):
        if data.draw(strat):
            data.mark_interesting()

    return accept


@pytest.mark.parametrize("n", [1, 5])
def test_terminates_shrinks(n, monkeypatch):
    db = InMemoryExampleDatabase()

    def generate_new_examples(self):
        self.cached_test_function((255,) * 1000)

    monkeypatch.setattr(
        ConjectureRunner, "generate_new_examples", generate_new_examples
    )
    monkeypatch.setattr(engine_module, "MAX_SHRINKS", n)

    runner = ConjectureRunner(
        slow_shrinker(),
        settings=settings(max_examples=5000, database=db),
        random=Random(0),
        database_key=b"key",
    )
    runner.run()
    (last_data,) = runner.interesting_examples.values()
    assert last_data.status == Status.INTERESTING
    assert runner.exit_reason == ExitReason.max_shrinks
    assert runner.shrinks == n
    in_db = set(db.data[runner.secondary_key])
    assert len(in_db) == n


def test_detects_flakiness():
    failed_once = False
    count = 0

    def tf(data):
        nonlocal count, failed_once
        data.draw_bytes(1, 1)
        count += 1
        if not failed_once:
            failed_once = True
            data.mark_interesting()

    runner = ConjectureRunner(tf)
    runner.run()
    assert runner.exit_reason == ExitReason.flaky
    assert count == MIN_TEST_CALLS + 1


def recur(i, data):
    if i >= 1:
        recur(i - 1, data)


@pytest.mark.skipif(PYPY, reason="stack tricks only work reliably on CPython")
def test_recursion_error_is_not_flaky():
    def tf(data):
        i = data.draw_integer(0, 2**16 - 1)
        try:
            recur(i, data)
        except RecursionError:
            data.mark_interesting()

    runner = ConjectureRunner(tf, settings=settings(derandomize=True))
    runner.run()
    assert runner.exit_reason == ExitReason.finished


def test_variadic_draw():
    def draw_list(data):
        result = []
        while True:
            data.start_span(SOME_LABEL)
            d = data.draw_integer(0, 2**8 - 1) & 7
            if d:
                result.append(data.draw_bytes(d, d))
            data.stop_span()
            if not d:
                break
        return result

    @run_to_nodes
    def nodes(data):
        if any(all(d) for d in draw_list(data)):
            data.mark_interesting()

    ls = draw_list(ConjectureData.for_choices([n.value for n in nodes]))
    assert len(ls) == 1
    assert len(ls[0]) == 1


def test_draw_to_overrun(monkeypatch):
    @run_to_nodes
    def nodes(data):
        d = (data.draw_bytes(1, 1)[0] - 8) & 0xFF
        data.draw_bytes(128 * d, 128 * d)
        if d >= 2:
            data.mark_interesting()

    assert tuple(n.value for n in nodes) == (bytes([10]),) + (bytes(128 * 2),)


def test_can_navigate_to_a_valid_example():
    def f(data):
        i = int_from_bytes(data.draw_bytes(2, 2))
        data.draw_bytes(i, i)
        data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(max_examples=5000, database=None))
    with buffer_size_limit(4):
        runner.run()
    assert runner.interesting_examples


def test_stops_after_max_examples_when_reading():
    key = b"key"

    db = InMemoryExampleDatabase()
    for i in range(10):
        db.save(key, bytes([i]))

    seen = []

    def f(data):
        seen.append(data.draw_bytes(1, 1))

    runner = ConjectureRunner(
        f, settings=settings(max_examples=1, database=db), database_key=key
    )
    runner.run()
    assert len(seen) == 1


def test_stops_after_max_examples_when_generating():
    seen = []

    def f(data):
        seen.append(data.draw_bytes(1, 1))

    runner = ConjectureRunner(f, settings=settings(max_examples=1, database=None))
    runner.run()
    assert len(seen) == 1


@pytest.mark.parametrize("examples", [1, 5, 20, 50])
def test_stops_after_max_examples_when_generating_more_bugs(examples):
    seen = []
    err_common = False
    err_rare = False

    def f(data):
        seen.append(data.draw_integer(0, 2**32 - 1))
        # Rare, potentially multi-error conditions
        nonlocal err_common, err_rare
        if seen[-1] > 2**31:
            err_rare = True
            raise ValueError
        err_common = True
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
    assert len(seen) <= examples + err_common + err_rare


def test_interleaving_engines():
    children = []

    @run_to_nodes
    def nodes(data):
        rnd = Random(data.draw_bytes(1, 1))

        def g(d2):
            d2.draw_bytes(1, 1)
            data.mark_interesting()

        runner = ConjectureRunner(g, random=rnd)
        children.append(runner)
        runner.run()
        if runner.interesting_examples:
            data.mark_interesting()

    assert tuple(n.value for n in nodes) == (b"\0",)
    for c in children:
        assert not c.interesting_examples


def test_phases_can_disable_shrinking():
    seen = set()

    def f(data):
        seen.add(bytes(data.draw_bytes(32, 32)))
        data.mark_interesting()

    runner = ConjectureRunner(
        f, settings=settings(database=None, phases=(Phase.reuse, Phase.generate))
    )
    runner.run()
    assert len(seen) == 1


def test_reuse_phase_runs_for_max_examples_if_generation_is_disabled():
    with deterministic_PRNG():
        db = InMemoryExampleDatabase()
        for i in range(256):
            db.save(b"key", choices_to_bytes([i]))
        seen = set()

        def test(data):
            seen.add(data.draw_integer(0, 2**8 - 1))

        ConjectureRunner(
            test,
            settings=settings(max_examples=100, database=db, phases=[Phase.reuse]),
            database_key=b"key",
        ).run()

        assert len(seen) == 100


def test_erratic_draws():
    n = 0

    with pytest.raises(FlakyStrategyDefinition):

        @run_to_nodes
        def nodes(data):
            nonlocal n
            data.draw_bytes(n, n)
            data.draw_bytes(255 - n, 255 - n)
            if n == 255:
                data.mark_interesting()
            else:
                n += 1


def test_no_read_no_shrink():
    count = 0

    @run_to_nodes
    def nodes(data):
        nonlocal count
        count += 1
        data.mark_interesting()

    assert nodes == ()
    assert count == 1


def test_one_dead_branch():
    with deterministic_PRNG():
        seen = set()

        @run_to_nodes
        def nodes(data):
            i = data.draw_bytes(1, 1)[0]
            if i > 0:
                data.mark_invalid()
            i = data.draw_bytes(1, 1)[0]
            if len(seen) < 255:
                seen.add(i)
            elif i not in seen:
                data.mark_interesting()


def test_does_not_save_on_interrupt():
    def interrupts(data):
        raise KeyboardInterrupt

    db = InMemoryExampleDatabase()
    runner = ConjectureRunner(
        interrupts, settings=settings(database=db), database_key=b"key"
    )
    with pytest.raises(KeyboardInterrupt):
        runner.run()
    assert not db.data


def test_saves_on_skip_exceptions_to_reraise():
    # skip exceptions should be saved to the db so we spend as little time as
    # possible exploring these tests in the future (if eg the skip is guarded
    # by a conditional that takes some time to hit). see also
    # https://github.com/HypothesisWorks/hypothesis/pull/4316#discussion_r2008912585
    def raises(data):
        pytest.skip()

    db = InMemoryExampleDatabase()
    runner = ConjectureRunner(
        raises, settings=settings(database=db), database_key=b"key"
    )
    with pytest.raises(pytest.skip.Exception):
        runner.run()

    assert len(db.data) == 1


def test_returns_forced():
    value = b"\0\1\2\3"

    @run_to_nodes
    def nodes(data):
        data.draw_bytes(len(value), len(value), forced=value)
        data.mark_interesting()

    assert tuple(n.value for n in nodes) == (value,)


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
        assert str(label) in str(e.value)
        assert not runner.interesting_examples

    return accept


def test_fails_health_check_for_all_invalid():
    @fails_health_check(HealthCheck.filter_too_much)
    def _(data):
        data.draw_bytes(2, 2)
        data.mark_invalid()


def test_fails_health_check_for_large_base():
    @fails_health_check(HealthCheck.large_base_example)
    def _(data):
        data.draw_bytes(10**6, 10**6)


def test_fails_health_check_for_large_non_base():
    @fails_health_check(HealthCheck.data_too_large)
    def _(data):
        if data.draw_integer(0, 2**8 - 1):
            data.draw_bytes(10**6, 10**6)


def test_fails_health_check_for_slow_draws():
    @fails_health_check(HealthCheck.too_slow)
    def _(data):
        data.draw(SLOW)


@pytest.mark.parametrize("n_large", [1, 5, 8, 15])
def test_can_shrink_variable_draws(n_large):
    target = 128 * n_large

    @st.composite
    def strategy(draw):
        n = draw(st.integers(0, 15))
        return [draw(st.integers(0, 255)) for _ in range(n)]

    ints = minimal(strategy(), lambda ints: sum(ints) >= target)
    # should look like [4, 255, 255, 255]
    assert ints == [target % 255] + [255] * (len(ints) - 1)


def test_can_shrink_variable_string_draws():
    @st.composite
    def strategy(draw):
        n = draw(st.integers(min_value=0, max_value=20))
        return draw(st.text(st.characters(codec="ascii"), min_size=n, max_size=n))

    s = minimal(strategy(), lambda s: len(s) >= 10 and "a" in s)

    # TODO_BETTER_SHRINK: this should be
    # assert s == "0" * 9 + "a"
    # but we first shrink to having a single a at the end of the string and then
    # fail to apply our special case invalid logic when shrinking the min_size n,
    # because that logic removes from the end of the string (which fails our
    # precondition).
    assert re.match("0+a", s)


def test_variable_size_string_increasing():
    # coverage test for min_size increasing during shrinking (because the test
    # function inverts n).
    # ...except this currently overruns instead and misses that check.
    @st.composite
    def strategy(draw):
        n = 10 - draw(st.integers(0, 10))
        return draw(st.text(st.characters(codec="ascii"), min_size=n, max_size=n))

    s = minimal(strategy(), lambda s: len(s) >= 5 and "a" in s)
    # TODO_BETTER_SHRINK: this should be
    # assert s == "0000a"
    # but instead shrinks to 00000000a.
    assert re.match("0+a", s)


def test_run_nothing():
    def f(data):
        raise AssertionError

    runner = ConjectureRunner(f, settings=settings(phases=()))
    runner.run()
    assert runner.call_count == 0


class Foo:
    def __repr__(self):
        return "stuff"


def test_debug_data(capsys):
    choices = (0, 1, 2)

    def f(data):
        for choice in choices:
            if data.draw(st.integers(0, 100)) != choice:
                data.mark_invalid()
            data.start_span(1)
            data.stop_span()
        data.mark_interesting()

    runner = ConjectureRunner(
        f,
        settings=settings(
            max_examples=5000,
            database=None,
            suppress_health_check=list(HealthCheck),
            verbosity=Verbosity.debug,
        ),
    )
    runner.cached_test_function(choices)
    runner.run()

    out, _ = capsys.readouterr()
    assert re.match(r"\d+ choices \(.*\) -> ", out)
    assert "INTERESTING" in out


def test_can_write_bytes_towards_the_end():
    buf = b"\1\2\3"

    def f(data):
        if data.draw_boolean():
            data.draw_bytes(5, 5)
            data.draw_bytes(len(buf), len(buf), forced=buf)
            assert data.choices[2] == buf

    with buffer_size_limit(15):
        ConjectureRunner(f).run()


def test_uniqueness_is_preserved_when_writing_at_beginning():
    seen = set()

    def f(data):
        data.draw_bytes(1, 1, forced=bytes(1))
        n = data.draw_integer(0, 2**3 - 1)
        assert n not in seen
        seen.add(n)

    runner = ConjectureRunner(f, settings=settings(max_examples=50))
    runner.run()
    assert runner.valid_examples == len(seen)


@pytest.mark.parametrize("skip_target", [False, True])
@pytest.mark.parametrize("initial_attempt", [(127,), (128,)])
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
        if data.draw_integer() >= 127:
            data.mark_interesting()

    runner = ConjectureRunner(
        f,
        settings=settings(database=db, max_examples=256),
        database_key=key,
        random=Random(0),
    )

    for n in range(256):
        if n != 127 or not skip_target:
            db.save(runner.secondary_key, choices_to_bytes([n]))
    runner.run()
    assert len(runner.interesting_examples) == 1
    for b in db.fetch(runner.secondary_key):
        assert choices_from_bytes(b)[0] >= 127
    assert len(list(db.fetch(runner.database_key))) == 1


def test_shrinks_both_interesting_examples(monkeypatch):
    def generate_new_examples(self):
        self.cached_test_function((1,))

    monkeypatch.setattr(
        ConjectureRunner, "generate_new_examples", generate_new_examples
    )

    def f(data):
        n = data.draw_integer(0, 2**8 - 1)
        data.mark_interesting(interesting_origin(n & 1))

    runner = ConjectureRunner(f, database_key=b"key")
    runner.run()
    assert runner.interesting_examples[interesting_origin(0)].choices == (0,)
    assert runner.interesting_examples[interesting_origin(1)].choices == (1,)


def test_discarding(monkeypatch):
    monkeypatch.setattr(Shrinker, "shrink", Shrinker.remove_discarded)
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.cached_test_function((False, True) * 10),
    )

    @run_to_nodes
    def nodes(data):
        count = 0
        while count < 10:
            data.start_span(SOME_LABEL)
            b = data.draw_boolean()
            if b:
                count += 1
            data.stop_span(discard=not b)
        data.mark_interesting()

    assert tuple(n.value for n in nodes) == (True,) * 10


def test_can_remove_discarded_data():
    @shrinking_from((0,) * 10 + (11,))
    def shrinker(data: ConjectureData):
        while True:
            data.start_span(SOME_LABEL)
            b = data.draw_integer(0, 2**8 - 1)
            data.stop_span(discard=(b == 0))
            if b == 11:
                break
        data.mark_interesting()

    shrinker.remove_discarded()
    assert shrinker.choices == (11,)


def test_discarding_iterates_to_fixed_point():
    @shrinking_from(list(range(100, -1, -1)))
    def shrinker(data: ConjectureData):
        data.start_span(0)
        data.draw_integer(0, 2**8 - 1)
        data.stop_span(discard=True)
        while data.draw_integer(0, 2**8 - 1):
            pass
        data.mark_interesting()

    shrinker.remove_discarded()
    assert shrinker.choices == (1, 0)


def test_discarding_is_not_fooled_by_empty_discards():
    @shrinking_from((1, 1))
    def shrinker(data: ConjectureData):
        data.draw_integer(0, 2**1 - 1)
        data.start_span(0)
        data.stop_span(discard=True)
        data.draw_integer(0, 2**1 - 1)
        data.mark_interesting()

    shrinker.remove_discarded()
    assert shrinker.shrink_target.has_discards


def test_discarding_can_fail():
    @shrinking_from((1,))
    def shrinker(data: ConjectureData):
        data.start_span(0)
        data.draw_boolean()
        data.stop_span(discard=True)
        data.mark_interesting()

    shrinker.remove_discarded()
    assert any(e.discarded and e.choice_count > 0 for e in shrinker.shrink_target.spans)


def test_shrinking_from_mostly_zero(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda self: self.cached_test_function((0,) * 5 + (2,)),
    )

    @run_to_nodes
    def nodes(data):
        s = [data.draw_integer(0, 2**8 - 1) for _ in range(6)]
        if any(s):
            data.mark_interesting()

    assert tuple(n.value for n in nodes) == (0,) * 5 + (1,)


def test_handles_nesting_of_discard_correctly(monkeypatch):
    monkeypatch.setattr(Shrinker, "shrink", Shrinker.remove_discarded)
    monkeypatch.setattr(
        ConjectureRunner,
        "generate_new_examples",
        lambda runner: runner.cached_test_function((False, False, True, True)),
    )

    @run_to_nodes
    def nodes(data):
        while True:
            data.start_span(SOME_LABEL)
            succeeded = data.draw_boolean()
            data.start_span(SOME_LABEL)
            data.draw_boolean()
            data.stop_span(discard=not succeeded)
            data.stop_span(discard=not succeeded)
            if succeeded:
                data.mark_interesting()

    assert tuple(n.value for n in nodes) == (True, True)


def test_database_clears_secondary_key():
    key = b"key"
    database = InMemoryExampleDatabase()

    def f(data):
        if data.draw_integer() == 10:
            data.mark_interesting()
        else:
            data.mark_invalid()

    runner = ConjectureRunner(
        f,
        settings=settings(
            max_examples=1, database=database, suppress_health_check=list(HealthCheck)
        ),
        database_key=key,
    )

    for i in range(10):
        database.save(runner.secondary_key, choices_to_bytes([i]))

    runner.cached_test_function((10,))
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
        if data.draw_integer() >= 5:
            data.mark_interesting()
        else:
            data.mark_invalid()

    runner = ConjectureRunner(
        f,
        settings=settings(
            max_examples=1, database=database, suppress_health_check=list(HealthCheck)
        ),
        database_key=key,
    )
    for i in range(10):
        database.save(runner.secondary_key, choices_to_bytes([i]))

    runner.cached_test_function((10,))
    assert runner.interesting_examples
    assert len(set(database.fetch(key))) == 1
    assert len(set(database.fetch(runner.secondary_key))) == 10

    runner.clear_secondary_key()

    assert len(set(database.fetch(key))) == 1
    assert {
        choices_from_bytes(b)[0] for b in database.fetch(runner.secondary_key)
    } == set(range(6, 11))

    (v,) = runner.interesting_examples.values()
    assert v.choices == (5,)


def test_exit_because_max_iterations():
    def f(data):
        data.draw_integer(0, 2**64 - 1)
        data.mark_invalid()

    runner = ConjectureRunner(
        f,
        settings=settings(
            max_examples=1, database=None, suppress_health_check=list(HealthCheck)
        ),
    )

    runner.run()

    assert runner.call_count <= 1000
    assert runner.exit_reason == ExitReason.max_iterations


def test_exit_because_shrink_phase_timeout(monkeypatch):
    val = 0

    def fast_time():
        nonlocal val
        val += 1000
        return val

    def f(data):
        if data.draw_integer(0, 2**64 - 1) > 2**33:
            data.mark_interesting()

    monkeypatch.setattr(time, "perf_counter", fast_time)
    runner = ConjectureRunner(f, settings=settings(database=None, max_examples=100_000))
    runner.run()
    assert runner.exit_reason == ExitReason.very_slow_shrinking
    assert runner.statistics["stopped-because"] == "shrinking was very slow"


def test_dependent_block_pairs_can_lower_to_zero():
    @shrinking_from((True, 1))
    def shrinker(data: ConjectureData):
        if data.draw_boolean():
            n = data.draw_integer(0, 2**16 - 1)
        else:
            n = data.draw_integer(0, 2**8 - 1)

        if n == 1:
            data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_individual_choices"])
    assert shrinker.choices == (False, 1)


def test_handle_size_too_large_during_dependent_lowering():
    @shrinking_from((True, 255, 0))
    def shrinker(data: ConjectureData):
        if data.draw_boolean():
            data.draw_integer(0, 2**16 - 1)
            data.mark_interesting()
        else:
            data.draw_integer(0, 2**8 - 1)

    shrinker.fixate_shrink_passes(["minimize_individual_choices"])


def test_block_may_grow_during_lexical_shrinking():
    @shrinking_from((2, 1, 1))
    def shrinker(data: ConjectureData):
        n = data.draw_integer(0, 2**8 - 1)
        if n == 2:
            data.draw_integer(0, 2**8 - 1)
            data.draw_integer(0, 2**8 - 1)
        else:
            data.draw_integer(0, 2**16 - 1)
        data.mark_interesting()

    shrinker.fixate_shrink_passes(["minimize_individual_choices"])
    assert shrinker.choices == (0, 0)


def test_lower_common_node_offset_does_nothing_when_changed_blocks_are_zero():
    @shrinking_from((True, False, True, False))
    def shrinker(data: ConjectureData):
        data.draw_boolean()
        data.draw_boolean()
        data.draw_boolean()
        data.draw_boolean()
        data.mark_interesting()

    shrinker.mark_changed(1)
    shrinker.mark_changed(3)
    shrinker.lower_common_node_offset()
    assert shrinker.choices == (True, False, True, False)


def test_lower_common_node_offset_ignores_zeros():
    @shrinking_from((2, 2, 0))
    def shrinker(data: ConjectureData):
        n = data.draw_integer(0, 2**8 - 1)
        data.draw_integer(0, 2**8 - 1)
        data.draw_integer(0, 2**8 - 1)
        if n > 0:
            data.mark_interesting()

    for i in range(3):
        shrinker.mark_changed(i)
    shrinker.lower_common_node_offset()
    assert shrinker.choices == (1, 1, 0)


def test_cached_test_function_returns_right_value():
    count = 0

    def tf(data):
        nonlocal count
        count += 1
        data.draw_integer(0, 3)
        data.mark_interesting()

    with deterministic_PRNG():
        runner = ConjectureRunner(tf, settings=TEST_SETTINGS)
        for _ in range(2):
            for choices in ((0,), (1,)):
                d = runner.cached_test_function(choices)
                assert d.status == Status.INTERESTING
                assert d.choices == choices
        assert count == 2


def test_cached_test_function_does_not_reinvoke_on_prefix():
    call_count = 0

    def test_function(data):
        nonlocal call_count
        call_count += 1
        data.draw_integer(0, 2**8 - 1)
        data.draw_bytes(1, 1, forced=bytes([7]))
        data.draw_integer(0, 2**8 - 1)

    with deterministic_PRNG():
        runner = ConjectureRunner(test_function, settings=TEST_SETTINGS)

        data = runner.cached_test_function((0, b"\0", 0))
        assert data.status == Status.VALID
        for n in [2, 1, 0]:
            d = runner.cached_test_function(data.choices[:n])
            assert d is Overrun
        assert call_count == 1


def test_will_evict_entries_from_the_cache(monkeypatch):
    monkeypatch.setattr(engine_module, "CACHE_SIZE", 5)
    count = 0

    def tf(data):
        nonlocal count
        data.draw_integer(0, 2**8 - 1)
        count += 1

    runner = ConjectureRunner(tf, settings=TEST_SETTINGS)

    for _ in range(3):
        for n in range(10):
            runner.cached_test_function((n,))

    # Because we exceeded the cache size, our previous
    # calls will have been evicted, so each call to
    # cached_test_function will have to reexecute.
    assert count == 30


def test_branch_ending_in_write():
    seen = set()

    def tf(data):
        count = 0
        while data.draw_boolean():
            count += 1

        if count > 1:
            data.draw_boolean(forced=False)

        assert data.nodes not in seen
        seen.add(data.nodes)

    with deterministic_PRNG():
        runner = ConjectureRunner(tf, settings=TEST_SETTINGS)

        for _ in range(100):
            prefix = runner.generate_novel_prefix()
            attempt = prefix + (False, False)
            data = runner.cached_test_function(attempt)
            assert data.status is Status.VALID
            assert startswith(attempt, data.choices)


def test_exhaust_space():
    with deterministic_PRNG():
        runner = ConjectureRunner(
            lambda data: data.draw_boolean(), settings=TEST_SETTINGS
        )
        runner.run()
        assert runner.tree.is_exhausted
        assert runner.valid_examples == 2


SMALL_COUNT_SETTINGS = settings(TEST_SETTINGS, max_examples=500)


def test_discards_kill_branches():
    seen = set()

    def test(data: ConjectureData):
        data.start_span(1)
        n1 = data.draw_integer(0, 9)
        data.stop_span(discard=n1 > 0)
        n2 = data.draw_integer(0, 9)
        n3 = data.draw_integer(0, 9)

        assert (n1, n2, n3) not in seen
        seen.add((n1, n2, n3))

    runner = ConjectureRunner(test, settings=SMALL_COUNT_SETTINGS)
    runner.run()
    assert runner.exit_reason is ExitReason.finished
    # 10 to explore the initial n1 = 0-9 statespace, then 100 to explore just
    # the (0, n1, n2) statespace, because every prefix other than 0 is a discard
    # and is not explored. Subtract the overlap, which occurs once at n1 = 0.
    assert len(seen) == 100 + 10 - 1


@pytest.mark.parametrize("n", range(1, 32))
def test_number_of_examples_in_integer_range_is_bounded(n):
    with deterministic_PRNG():

        def test(data):
            assert runner.call_count <= 2 * n
            data.draw_integer(0, n)

        runner = ConjectureRunner(test, settings=SMALL_COUNT_SETTINGS)
        runner.run()


def test_prefix_cannot_exceed_buffer_size(monkeypatch):
    buffer_size = 10

    with deterministic_PRNG(), buffer_size_limit(buffer_size):

        def test(data):
            while data.draw_boolean():
                assert data.length <= buffer_size
            assert data.length <= buffer_size

        runner = ConjectureRunner(test, settings=SMALL_COUNT_SETTINGS)
        runner.run()
        assert runner.valid_examples == buffer_size


def test_does_not_shrink_multiple_bugs_when_told_not_to():
    def test(data):
        m = data.draw_integer(0, 2**8 - 1)
        n = data.draw_integer(0, 2**8 - 1)

        if m > 0:
            data.mark_interesting(interesting_origin(1))
        if n > 5:
            data.mark_interesting(interesting_origin(2))

    with deterministic_PRNG():
        runner = ConjectureRunner(
            test, settings=settings(TEST_SETTINGS, report_multiple_bugs=False)
        )
        runner.cached_test_function((255, 255))
        runner.shrink_interesting_examples()

        results = {d.choices for d in runner.interesting_examples.values()}

    assert len(results.intersection({(0, 1), (1, 0)})) == 1


def test_does_not_keep_generating_when_multiple_bugs():
    def test(data):
        if data.draw_integer(0, 2**20 - 1) > 0:
            data.draw_integer(0, 2**20 - 1)
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

        value = data.draw_integer(0, 2**8 - 1)

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

        value = data.draw_integer(0, 2**16 - 1)

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
            data.target_observations[""] = data.draw_integer(0, 2**4 - 1)

        runner = ConjectureRunner(
            test,
            settings=settings(
                max_examples=5000,
                database=InMemoryExampleDatabase(),
                suppress_health_check=list(HealthCheck),
            ),
            database_key=b"stuff",
        )

        runner.run()

        assert len(runner.pareto_front) == 2**4


def test_pareto_front_contains_smallest_valid():
    with deterministic_PRNG():

        def test(data):
            data.target_observations[""] = 1
            data.draw_integer(0, 2**4 - 1)

        runner = ConjectureRunner(
            test,
            settings=settings(
                max_examples=5000,
                database=InMemoryExampleDatabase(),
                suppress_health_check=list(HealthCheck),
            ),
            database_key=b"stuff",
        )

        runner.run()

        assert len(runner.pareto_front) == 1


def test_replaces_all_dominated():
    def test(data):
        data.target_observations["m"] = 3 - data.draw_integer(0, 3)
        data.target_observations["n"] = 3 - data.draw_integer(0, 3)

    runner = ConjectureRunner(
        test,
        settings=settings(TEST_SETTINGS, database=InMemoryExampleDatabase()),
        database_key=b"stuff",
    )

    d1 = runner.cached_test_function((0, 1)).as_result()
    d2 = runner.cached_test_function((1, 0)).as_result()

    assert len(runner.pareto_front) == 2

    assert runner.pareto_front[0] == d1
    assert runner.pareto_front[1] == d2

    d3 = runner.cached_test_function((0, 0)).as_result()
    assert len(runner.pareto_front) == 1

    assert runner.pareto_front[0] == d3


def test_does_not_duplicate_elements():
    def test(data):
        data.target_observations["m"] = data.draw_integer(0, 2**8 - 1)

    runner = ConjectureRunner(
        test,
        settings=settings(TEST_SETTINGS, database=InMemoryExampleDatabase()),
        database_key=b"stuff",
    )
    d1 = runner.cached_test_function((1,)).as_result()

    assert len(runner.pareto_front) == 1
    # This can happen in practice if we e.g. reexecute a test because it has
    # expired from the cache. It's easier just to test it directly though
    # rather than simulate the failure mode.
    assert runner.pareto_front.add(d1)
    assert len(runner.pareto_front) == 1


def test_includes_right_hand_side_targets_in_dominance():
    def test(data):
        if data.draw_integer(0, 2**8 - 1):
            data.target_observations[""] = 10

    runner = ConjectureRunner(
        test,
        settings=settings(TEST_SETTINGS, database=InMemoryExampleDatabase()),
        database_key=b"stuff",
    )

    d1 = runner.cached_test_function((0,)).as_result()
    d2 = runner.cached_test_function((1,)).as_result()

    assert dominance(d1, d2) == DominanceRelation.NO_DOMINANCE


def test_smaller_interesting_dominates_larger_valid():
    def test(data):
        if data.draw_integer(0, 2**8 - 1) == 0:
            data.mark_interesting()

    runner = ConjectureRunner(
        test,
        settings=settings(TEST_SETTINGS, database=InMemoryExampleDatabase()),
        database_key=b"stuff",
    )

    d1 = runner.cached_test_function((0,)).as_result()
    d2 = runner.cached_test_function((1,)).as_result()
    assert dominance(d1, d2) == DominanceRelation.LEFT_DOMINATES


def test_runs_full_set_of_examples():
    def test(data):
        data.draw_integer(0, 2**64 - 1)

    runner = ConjectureRunner(
        test,
        settings=settings(TEST_SETTINGS, database=InMemoryExampleDatabase()),
        database_key=b"stuff",
    )

    runner.run()
    assert runner.valid_examples == TEST_SETTINGS.max_examples


def test_runs_optimisation_even_if_not_generating():
    def test(data):
        data.target_observations["n"] = data.draw_integer(0, 2**16 - 1)

    with deterministic_PRNG():
        runner = ConjectureRunner(
            test, settings=settings(TEST_SETTINGS, phases=[Phase.target])
        )
        runner.cached_test_function((0,))
        runner.run()

        assert runner.best_observed_targets["n"] == (2**16) - 1


def test_runs_optimisation_once_when_generating():
    def test(data):
        data.target_observations["n"] = data.draw_integer(0, 2**16 - 1)

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
        data.target_observations["n"] = data.draw_integer(0, 2**16 - 1)

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
        data.draw_integer()
        data.draw_integer()

    with deterministic_PRNG():
        runner = ConjectureRunner(test, settings=TEST_SETTINGS)

        d1 = runner.cached_test_function((0,), extend=10)
        assert runner.call_count == 1
        d2 = runner.cached_test_function((0,), extend=10)
        assert runner.call_count == 2
        assert d1.status is d2.status is Status.VALID


def test_does_cache_if_extend_is_not_used():
    calls = 0

    def test(data):
        nonlocal calls
        calls += 1
        data.draw_bytes(1, 1)

    with deterministic_PRNG():
        runner = ConjectureRunner(test, settings=TEST_SETTINGS)

        d1 = runner.cached_test_function((b"\0"), extend=8)
        d2 = runner.cached_test_function((b"\0"), extend=8)
        assert d1.status == d2.status == Status.VALID
        assert d1.choices == d2.choices
        assert calls == 1


def test_does_result_for_reuse():
    calls = 0

    def test(data):
        nonlocal calls
        calls += 1
        data.draw_bytes(1, 1)

    with deterministic_PRNG():
        runner = ConjectureRunner(test, settings=TEST_SETTINGS)

        d1 = runner.cached_test_function((b"\0"), extend=8)
        d2 = runner.cached_test_function(d1.choices)
        assert d1.status == d2.status == Status.VALID
        assert d1.nodes == d2.nodes
        assert calls == 1


def test_does_not_use_cached_overrun_if_extending():
    def test(data):
        data.draw_integer()
        data.draw_integer()

    with deterministic_PRNG():
        runner = ConjectureRunner(test, settings=TEST_SETTINGS)

        data = runner.cached_test_function((1,))
        assert data.status == Status.OVERRUN
        assert runner.call_count == 1

        # the choice sequence of (1,) maps to an overrun in the cache, but we
        # do not want to use this cache entry if we're extending.
        data = runner.cached_test_function((1,), extend=1)
        assert data.status == Status.VALID
        assert runner.call_count == 2


def test_uses_cached_overrun_if_not_extending():
    def test(data):
        data.draw_integer()
        data.draw_integer()

    with deterministic_PRNG():
        runner = ConjectureRunner(test, settings=TEST_SETTINGS)

        data = runner.cached_test_function((1,), extend=0)
        assert data.status is Status.OVERRUN
        assert runner.call_count == 1

        data = runner.cached_test_function((1,), extend=0)
        assert data.status is Status.OVERRUN
        assert runner.call_count == 1


def test_can_be_set_to_ignore_limits():
    def test(data):
        data.draw_integer(0, 2**8 - 1)

    with deterministic_PRNG():
        runner = ConjectureRunner(
            test, settings=settings(TEST_SETTINGS, max_examples=1), ignore_limits=True
        )
        for c in range(256):
            runner.cached_test_function((c,))

        assert runner.tree.is_exhausted


def test_too_slow_report():
    state = HealthCheckState()
    assert state.timing_report() == ""  # no draws recorded -> no report
    state.draw_times = {
        "generate:a": [2.0, 0.356789, 0.0],
        "generate:b": [0.1111111, 0.0, 0.002345678, 0.05, 0.123456, 0.1, 0.1, 0.1],
        "generate:c": [0.03, 0.05, 0.2],
        "generate:d": [0.04],
        "generate:e": [0.05, 0.01],
        "generate:f": [0.06],
        "generate:g": [0.07],
        "generate:h": [0.08],
        "generate:i": [0.09, 0.00001],
    }
    expected = """
      count | fraction |    slowest draws (seconds)
  a |    3  |     65%  |      --      --      --   0.357,  2.000
  b |    8  |     16%  |   0.100,  0.100,  0.100,  0.111,  0.123
  c |    3  |      8%  |      --      --   0.030,  0.050,  0.200
  i |    2  |      2%  |      --      --      --      --   0.090
  h |    1  |      2%  |      --      --      --      --   0.080
  (skipped 4 rows of fast draws)"""
    got = state.timing_report()
    print(got)
    assert expected == got


def _draw(cd, node):
    return getattr(cd, f"draw_{node.type}")(**node.constraints)


@given(nodes(was_forced=False))
def test_overruns_with_extend_are_not_cached(node):
    assume(compute_max_children(node.type, node.constraints) > 100)

    def test(cd):
        _draw(cd, node)
        _draw(cd, node)

    runner = ConjectureRunner(test)
    assert runner.call_count == 0

    data = runner.cached_test_function([node.value])
    assert runner.call_count == 1
    assert data.status is Status.OVERRUN

    # cache hit
    data = runner.cached_test_function([node.value])
    assert runner.call_count == 1
    assert data.status is Status.OVERRUN

    # cache miss
    data = runner.cached_test_function([node.value], extend="full")
    assert runner.call_count == 2
    assert data.status is Status.VALID


def test_simulate_to_evicted_data(monkeypatch):
    # test that we do not rely on the false invariant that correctly simulating
    # a data to a result means we have that result in the cache, due to e.g.
    # cache evictions (but also potentially other trickery).
    monkeypatch.setattr(engine_module, "CACHE_SIZE", 1)

    def test(data):
        data.draw_integer()

    runner = ConjectureRunner(test)
    runner.cached_test_function([0])
    # cache size is 1 so this evicts [0]
    runner.cached_test_function([1])
    assert runner.call_count == 2

    # we dont throw PreviouslyUnseenBehavior when simulating, but the result
    # was evicted to the cache so we will still call through to the test function.
    runner.tree.simulate_test_function(ConjectureData.for_choices([0]))
    runner.cached_test_function([0])
    assert runner.call_count == 3


@pytest.mark.parametrize(
    "strategy, condition",
    [
        (st.lists(st.integers(), min_size=5), lambda v: True),
        (st.lists(st.text(), min_size=2, unique=True), lambda v: True),
        (
            st.sampled_from(
                enum.Flag("LargeFlag", {f"bit{i}": enum.auto() for i in range(64)})
            ),
            lambda f: bit_count(f.value) > 1,
        ),
    ],
)
def test_mildly_complicated_strategies(strategy, condition):
    # There are some code paths in engine.py and shrinker.py that are easily
    # covered by shrinking any mildly compliated strategy and aren't worth
    # testing explicitly for. This covers those.
    minimal(strategy, condition)


def test_does_not_shrink_if_replaying_from_database():
    db = InMemoryExampleDatabase()
    key = b"foo"

    def f(data):
        if data.draw_integer(0, 255) == 123:
            data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(database=db), database_key=key)
    choices = (123,)
    runner.save_choices(choices)
    runner.shrink_interesting_examples = None
    runner.run()
    (last_data,) = runner.interesting_examples.values()
    assert last_data.choices == choices


def test_does_shrink_if_replaying_inexact_from_database():
    db = InMemoryExampleDatabase()
    key = b"foo"

    def f(data):
        data.draw_integer(0, 255)
        data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(database=db), database_key=key)
    runner.save_choices((123, 2))
    runner.run()
    (last_data,) = runner.interesting_examples.values()
    assert last_data.choices == (0,)


def test_stops_if_hits_interesting_early_and_only_want_one_bug():
    db = InMemoryExampleDatabase()
    key = b"foo"

    def f(data):
        data.draw_integer(0, 255)
        data.mark_interesting()

    runner = ConjectureRunner(
        f, settings=settings(database=db, report_multiple_bugs=False), database_key=key
    )
    for i in range(256):
        runner.save_choices([i])
    runner.run()
    assert runner.call_count == 1


def test_skips_secondary_if_interesting_is_found():
    db = InMemoryExampleDatabase()
    key = b"foo"

    def f(data):
        data.draw_integer(0, 255)
        data.mark_interesting()

    runner = ConjectureRunner(
        f,
        settings=settings(max_examples=1000, database=db, report_multiple_bugs=True),
        database_key=key,
    )
    for i in range(256):
        db.save(
            runner.database_key if i < 10 else runner.secondary_key,
            choices_to_bytes([i]),
        )
    runner.reuse_existing_examples()
    assert runner.call_count == 10


@pytest.mark.parametrize("key_name", ["database_key", "secondary_key"])
def test_discards_invalid_db_entries(key_name):
    with deterministic_PRNG():

        def test(data):
            data.draw_integer()
            data.mark_interesting()

        db = InMemoryExampleDatabase()
        runner = ConjectureRunner(
            test,
            # stop IN_COVERAGE_TESTS from overriding max_examples, which changes
            # db behavior
            settings=settings(database=db, max_examples=100),
            database_key=b"stuff",
        )
        key = getattr(runner, key_name)
        valid = choices_to_bytes([1])
        db.save(key, valid)
        for n in range(5):
            b = bytes([255, n])
            # save a bunch of invalid entries under the database key
            assert choices_from_bytes(b) is None
            db.save(key, b)

        assert len(set(db.fetch(key))) == 6
        # this will clear out the invalid entries and use the valid one
        runner.reuse_existing_examples()
        runner.clear_secondary_key()

        assert set(db.fetch(runner.database_key)) == {valid}
        assert runner.call_count == 1


def test_discards_invalid_db_entries_pareto():
    with deterministic_PRNG():

        def test(data):
            data.draw_integer()
            data.mark_interesting()

        db = InMemoryExampleDatabase()
        runner = ConjectureRunner(
            test,
            settings=settings(database=db, max_examples=100),
            database_key=b"stuff",
        )
        for n in range(5):
            b = bytes([255, n])
            assert choices_from_bytes(b) is None
            db.save(runner.pareto_key, b)

        assert len(set(db.fetch(runner.pareto_key))) == 5
        runner.reuse_existing_examples()

        assert not set(db.fetch(runner.database_key))
        assert not set(db.fetch(runner.pareto_key))
        assert runner.call_count == 0
