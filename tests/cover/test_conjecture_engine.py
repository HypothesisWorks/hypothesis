# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

import time
from random import seed as seed_random
from random import Random

import pytest

from hypothesis import Phase, HealthCheck, settings, unlimited
from hypothesis.errors import FailedHealthCheck
from tests.common.utils import all_values, checks_deprecated_behaviour
from hypothesis.database import ExampleDatabase, InMemoryExampleDatabase
from tests.common.strategies import SLOW, HardToShrink
from hypothesis.internal.compat import hbytes, hrange, int_from_bytes
from hypothesis.internal.conjecture.data import Status, ConjectureData
from hypothesis.internal.conjecture.engine import ConjectureRunner

MAX_SHRINKS = 1000


def run_to_buffer(f):
    runner = ConjectureRunner(f, settings=settings(
        max_examples=5000, max_iterations=10000, max_shrinks=MAX_SHRINKS,
        buffer_size=1024,
        database=None, perform_health_check=False,
    ))
    runner.run()
    assert runner.last_data.status == Status.INTERESTING
    return hbytes(runner.last_data.buffer)


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
    assert runner.last_data.status == Status.INTERESTING
    assert runner.last_data.buffer == value
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
    assert runner.last_data.status == Status.INTERESTING
    assert runner.shrinks == n
    in_db = set(
        v
        for vs in db.data.values()
        for v in vs
    )
    assert len(in_db) == n + 1


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
    assert runner.last_data.status == Status.INTERESTING
    return hbytes(runner.last_data.buffer)


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
    assert runner.last_data.status == Status.INTERESTING


@checks_deprecated_behaviour
def test_run_with_timeout_while_boring():
    def f(data):
        time.sleep(0.1)

    runner = ConjectureRunner(
        f, settings=settings(database=None, timeout=0.2))
    start = time.time()
    runner.run()
    assert time.time() <= start + 1
    assert runner.last_data.status == Status.VALID


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

    def call_with(buf):
        buf = hbytes(buf)

        def draw_bytes(data, n):
            return runner._ConjectureRunner__rewrite_for_novelty(
                data, buf[data.index:data.index + n])
        d = ConjectureData(
            draw_bytes=draw_bytes, max_length=2
        )
        runner.test_function(d)
        return d

    # First we ensure that all children of 0 are dead.
    for c in hrange(256):
        call_with([0, c])

    assert 1 in runner.dead

    # This must rewrite the first byte in order to get to a non-dead node.
    assert call_with([0, 0]).buffer == hbytes([1, 0])

    # This must rewrite the first byte in order to get to a non-dead node, but
    # the result of doing that is *still* dead, so it must rewrite the second
    # byte too.
    assert call_with([0, 0]).buffer == hbytes([1, 1])


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
        assert not any(b[:-1])

    runner = ConjectureRunner(
        f, settings=settings(buffer_size=11, perform_health_check=False))

    runner.run()


@pytest.mark.xfail(
    strict=True,
    reason="""This is currently demonstrating that __rewrite_for_novelty is
broken. It should start passing once we have a more sensible deduplication
mechanism.""")
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
    monkeypatch.setattr(
        ConjectureRunner, 'shrink', ConjectureRunner.greedy_interval_deletion
    )

    def f(data):
        if data.draw_bits(1):
            while data.draw_bits(8):
                pass
            data.mark_interesting()
    runner = ConjectureRunner(f, settings=settings(database=None))
    runner.run()
    x, = runner.interesting_examples.values()
    assert x.buffer == hbytes([1, 0])


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
    monkeypatch.setattr(
        ConjectureRunner, 'shrink', ConjectureRunner.reorder_blocks)

    @run_to_buffer
    def x(data):
        if sorted(
            data.draw_bits(8) for _ in hrange(len(target))
        ) == sorted(target):
            data.mark_interesting()

    assert x == target
