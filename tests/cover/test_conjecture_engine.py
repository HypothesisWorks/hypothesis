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

import re
import time
from random import Random
from random import seed as seed_random

import pytest

from hypothesis import Phase, Verbosity, HealthCheck, settings, unlimited
from hypothesis.errors import FailedHealthCheck
from tests.common.utils import all_values, checks_deprecated_behaviour
from hypothesis.database import ExampleDatabase, InMemoryExampleDatabase
from tests.common.strategies import SLOW, HardToShrink
from hypothesis.internal.compat import hbytes, hrange, int_from_bytes
from hypothesis.internal.conjecture.data import MAX_DEPTH, Status, \
    ConjectureData
from hypothesis.internal.conjecture.engine import Shrinker, \
    MultiShrinker, RunIsComplete, ConjectureRunner

MAX_SHRINKS = 1000


def patch_shrinking(monkeypatch, shrink):
    monkeypatch.setattr(
        Shrinker, 'escape_local_minimum', lambda self: None)
    monkeypatch.setattr(
        MultiShrinker, 'shrink', MultiShrinker.shrink_target_label,
    )
    monkeypatch.setattr(Shrinker, 'single_greedy_shrink_step', shrink)
    monkeypatch.setattr(Shrinker, 'is_trivial', lambda self: False)


def run_to_buffer(f):
    runner = ConjectureRunner(f, settings=settings(
        max_examples=5000, max_iterations=10000, max_shrinks=MAX_SHRINKS,
        buffer_size=1024,
        database=None, perform_health_check=False,
    ))
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
    key = b'hi there'
    db = ExampleDatabase()
    value = b'=\xc3\xe4l\x81\xe1\xc2H\xc9\xfb\x1a\xb6bM\xa8\x7f'
    db.save(key, value)

    def f(data):
        if data.draw_bytes(len(value)) == value:
            data.mark_interesting()
    runner = ConjectureRunner(
        f, settings=settings(database=db), database_key=key)
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


@pytest.mark.parametrize('n', [1, 5])
def test_terminates_shrinks(n, monkeypatch):
    db = InMemoryExampleDatabase()

    def generate_new_examples(self):
        def draw_bytes(data, n):
            return hbytes([255] * n)

        self.test_function(ConjectureData(
            draw_bytes=draw_bytes, max_length=self.settings.buffer_size))

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples', generate_new_examples)

    runner = ConjectureRunner(slow_shrinker(), settings=settings(
        max_examples=5000, max_iterations=10000, max_shrinks=n,
        database=db, timeout=unlimited,
    ), random=Random(0), database_key=b'key')
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
            data.start_example()
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
        d = (data.draw_bytes(1)[0] - 8) & 0xff
        data.draw_bytes(128 * d)
        if d >= 2:
            data.mark_interesting()
    assert x == hbytes([10]) + hbytes(128 * 2)


def test_can_navigate_to_a_valid_example():
    def f(data):
        i = int_from_bytes(data.draw_bytes(2))
        data.draw_bytes(i)
        data.mark_interesting()
    runner = ConjectureRunner(f, settings=settings(
        max_examples=5000, max_iterations=10000,
        buffer_size=2,
        database=None,
    ))
    runner.run()
    assert runner.interesting_examples


def test_stops_after_max_iterations_when_generating():
    key = b'key'
    value = b'rubber baby buggy bumpers'
    max_iterations = 100

    db = ExampleDatabase(':memory:')
    db.save(key, value)

    seen = []

    def f(data):
        seen.append(data.draw_bytes(len(value)))
        data.mark_invalid()

    runner = ConjectureRunner(f, settings=settings(
        max_examples=1, max_iterations=max_iterations,
        database=db, perform_health_check=False,
    ), database_key=key)
    runner.run()
    assert len(seen) == max_iterations
    assert value in seen


def test_stops_after_max_iterations_when_reading():
    key = b'key'
    max_iterations = 1

    db = ExampleDatabase(':memory:')
    for i in range(10):
        db.save(key, hbytes([i]))

    seen = []

    def f(data):
        seen.append(data.draw_bytes(1))
        data.mark_invalid()

    runner = ConjectureRunner(f, settings=settings(
        max_examples=1, max_iterations=max_iterations,
        database=db,
    ), database_key=key)
    runner.run()
    assert len(seen) == max_iterations


def test_stops_after_max_examples_when_reading():
    key = b'key'

    db = ExampleDatabase(':memory:')
    for i in range(10):
        db.save(key, hbytes([i]))

    seen = []

    def f(data):
        seen.append(data.draw_bytes(1))

    runner = ConjectureRunner(f, settings=settings(
        max_examples=1,
        database=db,
    ), database_key=key)
    runner.run()
    assert len(seen) == 1


def test_stops_after_max_examples_when_generating():
    seen = []

    def f(data):
        seen.append(data.draw_bytes(1))

    runner = ConjectureRunner(f, settings=settings(
        max_examples=1,
        database=None,
    ))
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
    assert x == b'\0'
    for c in children:
        assert not c.interesting_examples


@checks_deprecated_behaviour
def test_run_with_timeout_while_shrinking():
    def f(data):
        time.sleep(0.1)
        x = data.draw_bytes(32)
        if any(x):
            data.mark_interesting()

    runner = ConjectureRunner(
        f, settings=settings(database=None, timeout=0.2))
    start = time.time()
    runner.run()
    assert time.time() <= start + 1
    assert runner.interesting_examples


@checks_deprecated_behaviour
def test_run_with_timeout_while_boring():
    def f(data):
        time.sleep(0.1)

    runner = ConjectureRunner(
        f, settings=settings(database=None, timeout=0.2))
    start = time.time()
    runner.run()
    assert time.time() <= start + 1
    assert runner.valid_examples > 0


def test_max_shrinks_can_disable_shrinking():
    seen = set()

    def f(data):
        seen.add(hbytes(data.draw_bytes(32)))
        data.mark_interesting()

    runner = ConjectureRunner(
        f, settings=settings(database=None, max_shrinks=0,))
    runner.run()
    assert len(seen) == 1


def test_phases_can_disable_shrinking():
    seen = set()

    def f(data):
        seen.add(hbytes(data.draw_bytes(32)))
        data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(
        database=None, phases=(Phase.reuse, Phase.generate),
    ))
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
    assert x == b''
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
        key = data.draw_bytes(2)
        assert key not in seen
        seen.add(key)

    runner = ConjectureRunner(f, settings=settings(
        max_examples=10000, max_iterations=10000, max_shrinks=0,
        buffer_size=1024,
        database=None,
    ))

    for c in hrange(256):
        runner.cached_test_function([0, c])

    assert 1 in runner.dead

    runner.run()


def test_will_save_covering_examples():
    tags = {}

    def tagged(data):
        b = hbytes(data.draw_bytes(4))
        try:
            tag = tags[b]
        except KeyError:
            if len(tags) < 10:
                tag = len(tags)
                tags[b] = tag
            else:
                tag = None
        if tag is not None:
            data.add_tag(tag)

    db = InMemoryExampleDatabase()
    runner = ConjectureRunner(tagged, settings=settings(
        max_examples=100, max_iterations=10000, max_shrinks=0,
        buffer_size=1024,
        database=db,
    ), database_key=b'stuff')
    runner.run()
    assert len(all_values(db)) == len(tags)


def test_will_shrink_covering_examples():
    best = [None]
    replaced = []

    def tagged(data):
        b = hbytes(data.draw_bytes(4))
        if any(b):
            data.add_tag('nonzero')
            if best[0] is None:
                best[0] = b
            elif b < best[0]:
                replaced.append(best[0])
                best[0] = b

    db = InMemoryExampleDatabase()
    runner = ConjectureRunner(tagged, settings=settings(
        max_examples=100, max_iterations=10000, max_shrinks=0,
        buffer_size=1024,
        database=db,
    ), database_key=b'stuff')
    runner.run()
    saved = set(all_values(db))
    assert best[0] in saved
    for r in replaced:
        assert r not in saved


def test_can_cover_without_a_database_key():
    def tagged(data):
        data.add_tag(0)

    runner = ConjectureRunner(tagged, settings=settings(), database_key=None)
    runner.run()
    assert len(runner.covering_examples) == 1


def test_saves_on_interrupt():
    def interrupts(data):
        raise KeyboardInterrupt()

    db = InMemoryExampleDatabase()

    runner = ConjectureRunner(
        interrupts, settings=settings(database=db), database_key=b'key')

    with pytest.raises(KeyboardInterrupt):
        runner.run()
    assert db.data


def test_returns_written():
    value = hbytes(b'\0\1\2\3')

    @run_to_buffer
    def written(data):
        data.write(value)
        data.mark_interesting()

    assert value == written


def fails_health_check(label):
    def accept(f):
        runner = ConjectureRunner(f, settings=settings(
            max_examples=100, max_iterations=100, max_shrinks=0,
            buffer_size=1024, database=None, perform_health_check=True,
        ))

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


def test_fails_healthcheck_for_hung_test():
    @fails_health_check(HealthCheck.hung_test)
    def _(data):
        data.draw_bytes(1)
        time.sleep(3600)


@pytest.mark.parametrize('n_large', [1, 5, 8, 15])
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


@pytest.mark.parametrize('n', [1, 5, 8, 15])
def test_can_shrink_variable_draws_with_just_deletion(n, monkeypatch):
    patch_shrinking(
        monkeypatch, Shrinker.interval_deletion_with_block_lowering
    )
    # Would normally be added by minimize_individual_blocks, but we skip
    # that phase in this test.
    monkeypatch.setattr(
        Shrinker, 'is_shrinking_block', lambda self, i: i == 0
    )

    def gen(self):
        data = ConjectureData.for_buffer(
            [n] + [0] * (n - 1) + [1]
        )
        self.test_function(data)

    monkeypatch.setattr(ConjectureRunner, 'generate_new_examples', gen)

    @run_to_buffer
    def x(data):
        n = data.draw_bits(4)
        b = [data.draw_bits(8) for _ in hrange(n)]
        if any(b):
            data.mark_interesting()
    assert x == hbytes([1, 1])


def test_deletion_and_lowering_fails_to_shrink(monkeypatch):
    patch_shrinking(
        monkeypatch, Shrinker.interval_deletion_with_block_lowering
    )
    # Would normally be added by minimize_individual_blocks, but we skip
    # that phase in this test.
    monkeypatch.setattr(
        Shrinker, 'is_shrinking_block', lambda self, i: i == 0
    )

    def gen(self):
        data = ConjectureData.for_buffer(hbytes(10))
        self.test_function(data)

    monkeypatch.setattr(ConjectureRunner, 'generate_new_examples', gen)

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
        return 'stuff'


@pytest.mark.parametrize('event', ['hi', Foo()])
def test_note_events(event):
    def f(data):
        data.note_event(event)
        data.draw_bytes(1)

    runner = ConjectureRunner(f)
    runner.run()
    assert runner.event_call_counts[str(event)] == runner.call_count > 0


@pytest.mark.parametrize('count', [1, 3])
def test_debug_data(capsys, count):
    with settings(verbosity=Verbosity.debug):
        @run_to_buffer
        def f(data):
            for _ in hrange(count):
                data.draw_bytes(1)
            if sum(data.buffer) > 10:
                data.mark_interesting()
    out, _ = capsys.readouterr()
    assert re.match(u'\\d+ bytes \\[.*\\] -> ', out)


def test_zeroes_bytes_above_bound():
    def f(data):
        if data.draw_bits(1):
            x = data.draw_bytes(9)
            assert not any(x[4:8])

    ConjectureRunner(f, settings=settings(buffer_size=10)).run()


def test_can_write_bytes_towards_the_end():
    buf = b'\1\2\3'

    def f(data):
        if data.draw_bits(1):
            data.draw_bytes(5)
            data.write(hbytes(buf))
            assert hbytes(data.buffer[-len(buf):]) == buf

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
        f, settings=settings(buffer_size=11, perform_health_check=False))

    runner.run()


def test_uniqueness_is_preserved_when_writing_at_beginning():
    seen = set()

    def f(data):
        data.write(hbytes(1))
        n = data.draw_bits(3)
        assert n not in seen
        seen.add(n)

    runner = ConjectureRunner(
        f, settings=settings(max_examples=50))
    runner.run()
    assert runner.valid_examples == len(seen)


@pytest.mark.parametrize('skip_target', [False, True])
@pytest.mark.parametrize('initial_attempt', [127, 128])
def test_clears_out_its_database_on_shrinking(
    initial_attempt, skip_target, monkeypatch
):
    def generate_new_examples(self):
        self.test_function(
            ConjectureData.for_buffer(hbytes([initial_attempt])))

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples', generate_new_examples)

    key = b'key'
    db = InMemoryExampleDatabase()

    def f(data):
        if data.draw_bits(8) >= 127:
            data.mark_interesting()

    runner = ConjectureRunner(
        f, settings=settings(database=db, max_examples=256), database_key=key,
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


def test_saves_negated_examples_in_covering():
    def f(data):
        if data.draw_bits(8) & 1:
            data.add_tag('hi')

    runner = ConjectureRunner(f)
    runner.run()
    assert len(runner.target_selector.examples_by_tags) == 3


def test_can_delete_intervals(monkeypatch):
    def generate_new_examples(self):
        self.test_function(
            ConjectureData.for_buffer(hbytes([255] * 10 + [0])))

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples', generate_new_examples)
    patch_shrinking(monkeypatch, Shrinker.adaptive_example_deletion)

    def f(data):
        if data.draw_bits(1):
            while data.draw_bits(8):
                pass
            data.mark_interesting()
    runner = ConjectureRunner(f, settings=settings(database=None))
    runner.run()
    x, = runner.interesting_examples.values()
    assert x.buffer == hbytes([1, 0])


def test_detects_too_small_block_starts():
    def f(data):
        data.draw_bytes(8)
        data.mark_interesting()
    runner = ConjectureRunner(f, settings=settings(database=None))
    r = ConjectureData.for_buffer(hbytes(8))
    runner.test_function(r)
    assert r.status == Status.INTERESTING
    assert not runner.prescreen_buffer(hbytes([255] * 7))


def test_shrinks_both_interesting_examples(monkeypatch):
    def generate_new_examples(self):
        self.test_function(ConjectureData.for_buffer(hbytes([1])))

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples', generate_new_examples)

    def f(data):
        n = data.draw_bits(8)
        data.mark_interesting(n & 1)
    runner = ConjectureRunner(f, database_key=b'key')
    runner.run()
    assert runner.interesting_examples[0].buffer == hbytes([0])
    assert runner.interesting_examples[1].buffer == hbytes([1])


def test_reorder_blocks(monkeypatch):
    target = hbytes([1, 2, 3])

    def generate_new_examples(self):
        self.test_function(ConjectureData.for_buffer(hbytes(reversed(target))))

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples', generate_new_examples)
    patch_shrinking(monkeypatch, Shrinker.reorder_blocks)

    @run_to_buffer
    def x(data):
        if sorted(
            data.draw_bits(8) for _ in hrange(len(target))
        ) == sorted(target):
            data.mark_interesting()

    assert x == target


def test_duplicate_blocks_that_go_away(monkeypatch):
    patch_shrinking(monkeypatch, Shrinker.minimize_duplicated_blocks)
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(hbytes([1, 1, 1, 2] * 2 + [5] * 2)))
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
    patch_shrinking(monkeypatch, Shrinker.minimize_duplicated_blocks)
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(hbytes([18] * 20)))
    )

    @run_to_buffer
    def x(data):
        x = data.draw_bits(8)
        y = data.draw_bits(8)
        if x != y:
            data.mark_invalid()
        if x < 5:
            data.mark_invalid()
        b = [data.draw_bytes(1) for _ in hrange(x)]
        if len(set(b)) == 1:
            data.mark_interesting()
    assert x == hbytes([5] * 7)


def test_discarding(monkeypatch):
    patch_shrinking(monkeypatch, Shrinker.remove_discarded)
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(hbytes([0, 1] * 10)))
    )

    @run_to_buffer
    def x(data):
        count = 0
        while count < 10:
            data.start_example()
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


def test_discarding_runs_automatically(monkeypatch):
    patch_shrinking(monkeypatch, fixate(Shrinker.minimize_individual_blocks))
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(hbytes([1] * 10) + hbytes([11])))
    )

    @run_to_buffer
    def x(data):
        while True:
            data.start_example()
            b = data.draw_bits(8)
            data.stop_example(discard=(b == 0))
            if b == 11:
                break
        data.mark_interesting()
    assert x == hbytes(hbytes([11]))


def test_automatic_discarding_is_turned_off_if_it_does_not_work(monkeypatch):
    patch_shrinking(monkeypatch, fixate(Shrinker.minimize_individual_blocks))
    target = hbytes([0, 1]) * 5 + hbytes([11])
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(target))
    )

    existing = Shrinker.remove_discarded

    calls = [0]

    def remove_discarded(self):
        calls[0] += 1
        return existing(self)

    monkeypatch.setattr(Shrinker, 'remove_discarded', remove_discarded)

    @run_to_buffer
    def x(data):
        count = 0
        while True:
            data.start_example()
            b = data.draw_bits(8)
            if not b:
                count += 1
            data.stop_example(discard=(b == 0))
            if b == 11:
                break
        if count >= 5:
            data.mark_interesting()
    assert x == hbytes([0]) * 10 + hbytes([11])
    assert calls[0] == 1


def test_can_redraw_to_prevent_getting_stuck(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.cached_test_function(
            [10] + ([0] * 9 + [1]) * 2
        ))

    @run_to_buffer
    def x(data):
        n = data.draw_bits(8)
        x = data.draw_bytes(n)
        y = data.draw_bytes(n)
        if any(x) and any(y):
            data.mark_interesting()

    assert x == hbytes([1, 1, 1])


@pytest.mark.parametrize('bits', [3, 9])
@pytest.mark.parametrize('prefix', [b'', b'\0'])
@pytest.mark.parametrize('seed', [0])
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
        f, settings=settings(database=None, max_examples=size),
        random=Random(seed),
    )
    with pytest.raises(RunIsComplete):
        runner.cached_test_function(b'')
        for _ in hrange(size):
            p = runner.generate_novel_prefix()
            assert p not in seen_prefixes
            seen_prefixes.add(p)
            data = ConjectureData.for_buffer(
                hbytes(p + hbytes(2 + len(prefix))))
            runner.test_function(data)
            assert data.status == Status.VALID
            node = 0
            for b in data.buffer:
                node = runner.tree[node][b]
            assert node in runner.dead
    assert len(seen) == size


def test_depth_bounds_in_generation():
    depth = [0]

    def tree(data, n):
        depth[0] = max(depth[0], n)
        if data.draw_bits(8):
            data.start_example()
            tree(data, n + 1)
            tree(data, n + 1)
            data.stop_example()

    def f(data):
        tree(data, 0)

    runner = ConjectureRunner(
        f, settings=settings(database=None, max_examples=20))
    runner.run()
    assert 0 < depth[0] <= MAX_DEPTH


def test_shrinking_from_mostly_zero(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda self: self.cached_test_function(hbytes(5) + hbytes([2]))
    )

    @run_to_buffer
    def x(data):
        s = [data.draw_bits(8) for _ in hrange(6)]
        if any(s):
            data.mark_interesting()

    assert x == hbytes(5) + hbytes([1])


def test_handles_nesting_of_discard_correctly(monkeypatch):
    patch_shrinking(monkeypatch, Shrinker.remove_discarded)
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(hbytes([0, 0, 1, 1]))))

    @run_to_buffer
    def x(data):
        while True:
            data.start_example()
            succeeded = data.draw_bits(1)
            data.start_example()
            data.draw_bits(1)
            data.stop_example(discard=not succeeded)
            data.stop_example(discard=not succeeded)
            if succeeded:
                data.mark_interesting()

    assert x == hbytes([1, 1])


def test_can_zero_subintervals(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.cached_test_function(
            hbytes([3, 0, 0, 0, 1]) * 10
        ))

    patch_shrinking(monkeypatch, fixate(Shrinker.zero_draws))

    @run_to_buffer
    def x(data):
        for _ in hrange(10):
            data.start_example()
            n = data.draw_bits(8)
            data.draw_bytes(n)
            data.stop_example()
            if data.draw_bits(8) != 1:
                return
        data.mark_interesting()
    assert x == hbytes([0, 1]) * 10


def test_can_pass_to_a_subinterval(monkeypatch):
    marker = hbytes([4, 3, 2, 1])

    initial = hbytes(len(marker) * 4) + marker

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.cached_test_function(initial))

    patch_shrinking(monkeypatch, Shrinker.pass_to_interval)

    @run_to_buffer
    def x(data):
        while True:
            b = data.draw_bytes(len(marker))
            if any(b):
                break
        if hbytes(data.buffer) in (marker, initial):
            data.mark_interesting()

    assert x == marker


def test_can_handle_size_changing_in_reordering(monkeypatch):
    patch_shrinking(monkeypatch, Shrinker.reorder_bytes)
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(hbytes([13, 7, 0]))))

    @run_to_buffer
    def x(data):
        n = data.draw_bits(8)
        if n == 0:
            data.mark_invalid()
        if n != 7:
            data.draw_bits(8)
        data.draw_bits(8)
        data.mark_interesting()

    assert x == hbytes([7, 13])


def test_can_handle_size_changing_in_reordering_with_unsortable_bits(
    monkeypatch
):
    """Forces the reordering to pass to run its quadratic comparison of every
    pair and changes the size during that pass."""

    patch_shrinking(monkeypatch, Shrinker.reorder_bytes)
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(hbytes([13, 14, 7, 3]))))

    @run_to_buffer
    def x(data):
        n = data.draw_bits(8)
        if n not in (7, 13):
            data.mark_invalid()

        # Having this marker here means that sorting the high bytes will move
        # this one to the right, which will make the test case invalid.
        if data.draw_bits(8) != 14:
            data.mark_invalid()
        if n != 7:
            data.draw_bits(8)
        data.draw_bits(8)
        data.mark_interesting()

    assert x == hbytes([7, 14, 13])


def test_will_immediately_reorder_to_sorted(monkeypatch):
    patch_shrinking(monkeypatch, Shrinker.reorder_bytes)
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(hbytes(list(range(10, 0, -1))))))

    @run_to_buffer
    def x(data):
        for _ in hrange(10):
            data.draw_bits(8)
        data.mark_interesting()

    assert x == hbytes(list(hrange(1, 11)))


def test_reorder_can_fail_to_sort(monkeypatch):
    target = hbytes([1, 0, 0, 3, 2, 1])

    patch_shrinking(monkeypatch, Shrinker.reorder_bytes)
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(target)))

    @run_to_buffer
    def x(data):
        for _ in hrange(len(target)):
            data.draw_bits(8)
        if hbytes(data.buffer) == target:
            data.mark_interesting()

    assert x == target


def test_reordering_interaction_with_writing(monkeypatch):
    patch_shrinking(monkeypatch, Shrinker.reorder_bytes)
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([3, 2, 1])))

    @run_to_buffer
    def x(data):
        m = data.draw_bits(8)
        if m == 2:
            data.write(hbytes(2))
        elif m == 1:
            data.mark_invalid()
        else:
            data.draw_bits(8)
            data.draw_bits(8)
        data.mark_interesting()

    assert x == hbytes([0, 0, 2])


def test_shrinking_blocks_from_common_offset(monkeypatch):
    patch_shrinking(
        monkeypatch, lambda self: (
            self.minimize_individual_blocks(),
            self.lower_common_block_offset(),
        )
    )

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([11, 10])))

    @run_to_buffer
    def x(data):
        m = data.draw_bits(8)
        n = data.draw_bits(8)
        if abs(m - n) <= 1:
            data.mark_interesting()
    assert x == hbytes([1, 0])


def test_handle_empty_draws(monkeypatch):
    patch_shrinking(monkeypatch, Shrinker.adaptive_example_deletion)

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(ConjectureData.for_buffer(
            [1, 1, 0])))

    @run_to_buffer
    def x(data):
        while True:
            data.start_example()
            n = data.draw_bits(1)
            data.start_example()
            data.stop_example()
            data.stop_example(discard=n > 0)
            if not n:
                break
        data.mark_interesting()
    assert x == hbytes([0])


def test_shrinks_multiple_at_once(monkeypatch):
    n = 6

    def test_function(data):
        data.mark_interesting(data.draw_bits(16) % n)

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(ConjectureData.for_buffer(
            [255, 255])))

    runner = ConjectureRunner(test_function, settings=settings(
        max_examples=5000, max_iterations=10000, max_shrinks=MAX_SHRINKS,
        buffer_size=1024,
        database=None, perform_health_check=False,
    ))
    runner.run()
    assert len(runner.interesting_examples) == n
    assert {d.buffer for d in runner.interesting_examples.values()} == {
        hbytes([0, k]) for k in hrange(n)
    }
