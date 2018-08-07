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
from mock import MagicMock

from hypothesis import Phase, Verbosity, HealthCheck, settings, unlimited
from hypothesis.errors import FailedHealthCheck
from tests.common.utils import no_shrink, all_values, \
    checks_deprecated_behaviour
from hypothesis.database import ExampleDatabase, InMemoryExampleDatabase
from tests.common.strategies import SLOW, HardToShrink
from hypothesis.internal.compat import hbytes, hrange, int_from_bytes
from hypothesis.internal.entropy import deterministic_PRNG
from hypothesis.internal.conjecture.data import MAX_DEPTH, Status, \
    ConjectureData
from hypothesis.internal.conjecture.utils import Sampler, \
    calc_label_from_name
from hypothesis.internal.conjecture.engine import Negated, Shrinker, \
    StopTest, ExitReason, RunIsComplete, TargetSelector, \
    ConjectureRunner, universal

SOME_LABEL = calc_label_from_name('some label')


def run_to_buffer(f):
    with deterministic_PRNG():
        runner = ConjectureRunner(f, settings=settings(
            max_examples=5000, buffer_size=1024,
            database=None, suppress_health_check=HealthCheck.all(),
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
    from hypothesis.internal.conjecture import engine
    db = InMemoryExampleDatabase()

    def generate_new_examples(self):
        def draw_bytes(data, n):
            return hbytes([255] * n)

        self.test_function(ConjectureData(
            draw_bytes=draw_bytes, max_length=self.settings.buffer_size))

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples', generate_new_examples)
    monkeypatch.setattr(engine, 'MAX_SHRINKS', n)

    runner = ConjectureRunner(slow_shrinker(), settings=settings(
        max_examples=5000, database=db, timeout=unlimited,
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
        max_examples=5000, buffer_size=2, database=None,
    ))
    runner.run()
    assert runner.interesting_examples


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


@checks_deprecated_behaviour
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
        max_examples=10000, phases=no_shrink, buffer_size=1024, database=None,
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
        max_examples=100, phases=no_shrink, buffer_size=1024, database=db,
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
        max_examples=100, phases=no_shrink, buffer_size=1024, database=db,
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


def fails_health_check(label, **kwargs):
    def accept(f):
        runner = ConjectureRunner(f, settings=settings(
            max_examples=100, phases=no_shrink, buffer_size=1024,
            database=None, **kwargs
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
    @fails_health_check(HealthCheck.hung_test, timeout=unlimited)
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
        Shrinker, 'shrink', Shrinker.example_deletion_with_block_lowering
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
    def f(data):
        for _ in hrange(count):
            data.draw_bytes(1)
        if sum(data.buffer) > 10:
            data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(
        max_examples=5000, buffer_size=1024,
        database=None, suppress_health_check=HealthCheck.all(),
        verbosity=Verbosity.debug
    ))
    runner.run()

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
        f, settings=settings(
            max_examples=100,
            buffer_size=11, suppress_health_check=HealthCheck.all()))

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
    """Check that every key in examples_by_tags is either the universal tag or
    a Negated of some other key in the dict."""
    def f(data):
        if data.draw_bits(8) & 1:
            data.add_tag('hi')

    runner = ConjectureRunner(f)
    runner.run()
    tags = set(runner.target_selector.examples_by_tags)
    negated_tags = {t for t in tags if isinstance(t, Negated)}
    not_universal_or_negated = tags - negated_tags - {universal}
    assert not_universal_or_negated > set()
    assert {t.tag for t in negated_tags} == not_universal_or_negated


def test_can_delete_intervals(monkeypatch):
    def generate_new_examples(self):
        self.test_function(
            ConjectureData.for_buffer(hbytes([255] * 10 + [1, 3])))

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples', generate_new_examples)
    monkeypatch.setattr(
        Shrinker, 'shrink', fixate(Shrinker.adaptive_example_deletion)
    )

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


def test_duplicate_blocks_that_go_away(monkeypatch):
    monkeypatch.setattr(
        Shrinker, 'shrink', Shrinker.minimize_duplicated_blocks)
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
    monkeypatch.setattr(
        Shrinker, 'shrink', Shrinker.minimize_duplicated_blocks)
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
    monkeypatch.setattr(
        Shrinker, 'shrink', Shrinker.remove_discarded)
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(hbytes([0, 1] * 10)))
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


def test_automatic_discarding_is_turned_off_if_it_does_not_work(monkeypatch):
    monkeypatch.setattr(
        Shrinker, 'shrink', fixate(Shrinker.minimize_individual_blocks))
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
            data.start_example(SOME_LABEL)
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

    def tails(data, n):
        depth[0] = max(depth[0], n)
        if data.draw_bits(8):
            data.start_example(SOME_LABEL)
            tails(data, n + 1)
            data.stop_example()

    def f(data):
        tails(data, 0)

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
    monkeypatch.setattr(
        Shrinker, 'shrink', Shrinker.remove_discarded)
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer(hbytes([0, 0, 1, 1]))))

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
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.cached_test_function(
            hbytes([3, 0, 0, 0, 1]) * 10
        ))

    monkeypatch.setattr(
        Shrinker, 'shrink', fixate(Shrinker.adaptive_example_deletion)
    )

    @run_to_buffer
    def x(data):
        for _ in hrange(10):
            data.start_example(SOME_LABEL)
            n = data.draw_bits(8)
            data.draw_bytes(n)
            data.stop_example()
            if data.draw_bits(8) != 1:
                return
        data.mark_interesting()
    assert x == hbytes([0, 1]) * 10


def test_can_pass_to_a_child(monkeypatch):
    marker = hbytes([4, 3, 2, 1])

    initial = hbytes(len(marker) * 4) + marker

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.cached_test_function(initial))

    monkeypatch.setattr(Shrinker, 'shrink', Shrinker.pass_to_child)

    @run_to_buffer
    def x(data):
        data.start_example(1)
        while True:
            data.start_example(1)
            b = data.draw_bytes(len(marker))
            data.stop_example(1)
            if any(b):
                break
        data.stop_example()
        if hbytes(data.buffer) in (marker, initial):
            data.mark_interesting()
    assert x == marker


def test_pass_to_child_only_passes_to_same_label():
    @shrinking_from(list(range(10)))
    def shrinker(data):
        data.start_example(1)
        data.draw_bits(1)
        data.start_example(2)
        data.draw_bits(1)
        data.stop_example()
        data.stop_example()
        data.mark_interesting()
    initial = shrinker.calls
    shrinker.pass_to_child()
    assert shrinker.calls == initial


def test_can_pass_to_an_indirect_descendant(monkeypatch):
    initial = hbytes([
        1, 10,
        0, 0,
        1, 0,
        0, 10,
        0, 0,
    ])

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.cached_test_function(initial))

    monkeypatch.setattr(Shrinker, 'shrink', Shrinker.pass_to_descendant)

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


def test_shrinking_block_pairs(monkeypatch):
    monkeypatch.setattr(
        Shrinker, 'shrink', lambda self: (
            self.shrink_offset_pairs()
        )
    )

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([12, 10])))

    @run_to_buffer
    def x(data):
        m = data.draw_bits(8)
        n = data.draw_bits(8)
        if m == n + 2:
            data.mark_interesting()
    assert x == hbytes([2, 0])


def test_non_minimal_pair_shrink(monkeypatch):
    monkeypatch.setattr(
        Shrinker, 'shrink', lambda self: (
            self.shrink_offset_pairs()
        )
    )

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([12, 10])))

    @run_to_buffer
    def x(data):
        m = data.draw_bits(8)
        if m < 5:
            data.mark_invalid()
        if m == 5:
            data.mark_interesting()
        n = data.draw_bits(8)
        if m == n + 2:
            data.mark_interesting()
    assert x == hbytes([5])


def test_buffer_changes_during_pair_shrink(monkeypatch):
    monkeypatch.setattr(
        Shrinker, 'shrink', lambda self: (
            self.shrink_offset_pairs()
        )
    )

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([12, 10])))

    @run_to_buffer
    def x(data):
        m = data.draw_bits(8)
        if m < 5:
            data.mark_invalid()
        if m == 5:
            data.write(hbytes([1]))
            data.mark_interesting()
        n = data.draw_bits(8)
        if m == n + 2:
            data.mark_interesting()
    assert x == hbytes([5, 1])


def test_buffer_changes_during_pair_shrink_stays_interesting(monkeypatch):
    monkeypatch.setattr(
        Shrinker, 'shrink', lambda self: (
            self.shrink_offset_pairs()
        )
    )

    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([12, 10])))

    @run_to_buffer
    def x(data):
        m = data.draw_bits(8)
        if m == 12:
            data.draw_bits(8)
        if m >= 9:
            data.mark_interesting()
    assert len(x) == 1


def test_shrinking_blocks_from_common_offset(monkeypatch):
    monkeypatch.setattr(
        Shrinker, 'shrink', lambda self: (
            # Run minimize_individual_blocks twice so we have both blocks show
            # as changed regardless of which order this happens in.
            self.minimize_individual_blocks(),
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
        if abs(m - n) <= 1 and max(m, n) > 0:
            data.mark_interesting()
    assert sorted(x) == [0, 1]


def test_handle_empty_draws(monkeypatch):
    monkeypatch.setattr(
        Shrinker, 'shrink', Shrinker.adaptive_example_deletion)

    lambda runner: runner.test_function(ConjectureData.for_buffer(
        [1, 1, 0]))

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
    big = hbytes(b'\xff') * 512

    def f(data):
        data.write(big)
        data.draw_bits(63)

    with deterministic_PRNG():
        runner = ConjectureRunner(f, settings=settings(
            max_examples=5000, buffer_size=1024,
            database=None, suppress_health_check=HealthCheck.all(),
        ))
        runner.run()

    assert runner.exit_reason == ExitReason.finished


@pytest.mark.parametrize('lo', [0, 1, 50])
def test_can_shrink_additively(monkeypatch, lo):
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda self: self.test_function(
            ConjectureData.for_buffer(hbytes([100, 100]))))

    @run_to_buffer
    def x(data):
        m = data.draw_bits(8)
        n = data.draw_bits(8)
        if m >= lo and m + n == 200:
            data.mark_interesting()

    assert list(x) == [lo, 200 - lo]


def test_can_shrink_additively_losing_size(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda self: self.test_function(
            ConjectureData.for_buffer(hbytes([100, 100]))))

    monkeypatch.setattr(
        Shrinker, 'shrink', lambda self: (
            self.minimize_block_pairs_retaining_sum(),
        )
    )

    @run_to_buffer
    def x(data):
        m = data.draw_bits(8)
        if m >= 10:
            if m <= 50:
                data.mark_interesting()
            else:
                n = data.draw_bits(8)
                if m + n == 200:
                    data.mark_interesting()
    assert len(x) == 1


def test_can_reorder_examples(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([1, 0, 1, 1, 0, 1, 0, 0, 0])))

    monkeypatch.setattr(
        Shrinker, 'shrink', Shrinker.reorder_examples,
    )

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
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([1])))

    monkeypatch.setattr(
        Shrinker, 'shrink',
        lambda self: self.incorporate_new_buffer(hbytes([2]))
    )

    @run_to_buffer
    def x(data):
        data.draw_bits(2)
        data.mark_interesting()

    assert list(x) == [1]


def test_block_deletion_can_delete_short_ranges(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([
                v for i in range(5) for _ in range(i + 1) for v in [0, i]])))

    monkeypatch.setattr(Shrinker, 'shrink', Shrinker.block_deletion)

    @run_to_buffer
    def x(data):
        while True:
            n = data.draw_bits(16)
            for _ in range(n):
                if data.draw_bits(16) != n:
                    data.mark_invalid()
            if n == 4:
                data.mark_interesting()

    assert list(x) == [0, 4] * 5


def test_try_shrinking_blocks_ignores_overrun_blocks(monkeypatch):
    monkeypatch.setattr(
        ConjectureRunner, 'generate_new_examples',
        lambda runner: runner.test_function(
            ConjectureData.for_buffer([3, 3, 0, 1])))

    monkeypatch.setattr(
        Shrinker, 'shrink',
        lambda self: self.try_shrinking_blocks(
            (0, 1, 5), hbytes([2])
        ),
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


def test_only_calls_discard_at_top_level_pass():
    def tree(data):
        data.start_example('tree')
        result = 1
        if data.draw_bits(1):
            result += max(tree(data), tree(data))
        data.stop_example()
        return result

    def f(data):
        if tree(data) == 3:
            data.mark_interesting()

    runner = ConjectureRunner(f, settings=settings(
        max_examples=1, buffer_size=1024,
        database=None, suppress_health_check=HealthCheck.all(),
    ))

    runner.test_function(ConjectureData.for_buffer([
        1, 0, 1, 0, 0,
    ]))

    assert runner.interesting_examples
    last_data, = runner.interesting_examples.values()

    shrinker = runner.new_shrinker(
        last_data, lambda d: d.status == Status.INTERESTING
    )

    shrinker.remove_discarded = MagicMock(return_value=None)

    shrinker.adaptive_example_deletion()

    assert shrinker.remove_discarded.call_count == 1


def shrinking_from(start):
    def accept(f):
        with deterministic_PRNG():
            runner = ConjectureRunner(f, settings=settings(
                max_examples=5000, buffer_size=1024,
                database=None, suppress_health_check=HealthCheck.all(),
            ))
            runner.test_function(ConjectureData.for_buffer(start))
            assert runner.interesting_examples
            last_data, = runner.interesting_examples.values()
            return runner.new_shrinker(
                last_data, lambda d: d.status == Status.INTERESTING
            )
    return accept


def test_dependent_block_pairs_is_up_to_shrinking_integers():
    # Unit test extracted from a failure in tests/nocover/test_integers.py
    distribution = Sampler([
        4.0, 8.0, 1.0, 1.0, 0.5
    ])

    sizes = [8, 16, 32, 64, 128]

    @shrinking_from(b'\x03\x01\x00\x00\x00\x00\x00\x01\x00\x02\x01')
    def shrinker(data):
        size = sizes[distribution.sample(data)]
        result = data.draw_bits(size)
        sign = (-1) ** (result & 1)
        result = (result >> 1) * sign
        cap = data.draw_bits(8)

        if result >= 32768 and cap == 1:
            data.mark_interesting()

    shrinker.minimize_individual_blocks()
    assert list(shrinker.shrink_target.buffer) == [
        1, 1, 0, 1, 0, 0, 1
    ]


def test_finding_a_minimal_balanced_binary_tree():
    # Tests iteration while the shape of the thing being iterated over can
    # change. In particular the current example can go from trivial to non
    # trivial.

    def tree(data):
        # Returns height of a binary tree and whether it is height balanced.
        data.start_example('tree')
        n = data.draw_bits(1)
        if n == 0:
            result = (1, True)
        else:
            h1, b1 = tree(data)
            h2, b2 = tree(data)
            result = (1 + max(h1, h2), b1 and b2 and abs(h1 - h2) <= 1)
        data.stop_example('tree')
        return result

    # Starting from an unbalanced tree of depth six
    @shrinking_from([1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
    def shrinker(data):
        _, b = tree(data)
        if not b:
            data.mark_interesting()

    shrinker.adaptive_example_deletion()
    shrinker.reorder_examples()

    assert list(shrinker.shrink_target.buffer) == [
        1, 0, 1, 0, 1, 0, 0
    ]


def test_database_clears_secondary_key():
    key = b'key'
    database = InMemoryExampleDatabase()

    def f(data):
        if data.draw_bits(8) == 10:
            data.mark_interesting()
        else:
            data.mark_invalid()

    runner = ConjectureRunner(f, settings=settings(
        max_examples=1, buffer_size=1024,
        database=database, suppress_health_check=HealthCheck.all(),
    ), database_key=key)

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
    key = b'key'
    database = InMemoryExampleDatabase()

    def f(data):
        if data.draw_bits(8) >= 5:
            data.mark_interesting()
        else:
            data.mark_invalid()

    runner = ConjectureRunner(f, settings=settings(
        max_examples=1, buffer_size=1024,
        database=database, suppress_health_check=HealthCheck.all(),
    ), database_key=key)

    for i in range(10):
        database.save(runner.secondary_key, hbytes([i]))

    runner.test_function(ConjectureData.for_buffer(hbytes([10])))
    assert runner.interesting_examples

    assert len(set(database.fetch(key))) == 1
    assert len(set(database.fetch(runner.secondary_key))) == 10

    runner.clear_secondary_key()

    assert len(set(database.fetch(key))) == 1
    assert set(
        map(int_from_bytes, database.fetch(runner.secondary_key))
    ) == set(range(6, 11))

    v, = runner.interesting_examples.values()

    assert list(v.buffer) == [5]


def test_exit_because_max_iterations():

    def f(data):
        data.draw_bits(64)
        data.mark_invalid()

    runner = ConjectureRunner(f, settings=settings(
        max_examples=1, buffer_size=1024,
        database=None, suppress_health_check=HealthCheck.all(),
    ))

    runner.run()

    assert runner.call_count <= 1000
    assert runner.exit_reason == ExitReason.max_iterations


def test_target_selector_tags():
    selector = TargetSelector(Random(0))

    tag1 = 'some tag'
    tag2 = 'some other tag'

    data = ConjectureData.for_buffer(hbytes(10))
    try:
        data.draw_bits(10)
        data.add_tag(tag1)
        data.mark_interesting()
    except StopTest:
        pass

    assert selector.has_tag(universal, data)
    assert selector.has_tag(tag1, data)
    assert selector.has_tag(Negated(tag2), data)
    assert not selector.has_tag(Negated(tag1), data)
    assert not selector.has_tag(tag2, data)


def test_skips_non_payload_blocks_when_reducing_sum():
    @shrinking_from([10, 10, 10])
    def shrinker(data):
        if sum([data.draw_bits(8) for _ in range(3)]) == 30:
            data.mark_interesting()

    shrinker.is_payload_block = lambda b: b != 1
    shrinker.minimize_block_pairs_retaining_sum()
    assert list(shrinker.shrink_target.buffer) == [0, 10, 20]


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


def test_adaptive_deletion_will_zero_blocks():
    @shrinking_from([1, 1, 1])
    def shrinker(data):
        n = data.draw_bits(1)
        data.draw_bits(1)
        m = data.draw_bits(1)
        if n == m == 1:
            data.mark_interesting()
    shrinker.adaptive_example_deletion()
    assert list(shrinker.shrink_target.buffer) == [1, 0, 1]


def test_non_trivial_examples():
    initial = hbytes([1, 0, 1])

    @shrinking_from(initial)
    def shrinker(data):
        data.draw_bits(1)
        data.draw_bits(1)
        data.draw_bits(1)
        data.mark_interesting()

    assert {
        (ex.start, ex.end) for ex in shrinker.each_non_trivial_example()
    } == {(0, 3), (0, 1), (2, 3)}


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

    endpoints = {
        (ex.start, ex.end) for ex in shrinker.each_non_trivial_example()
    }

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


def test_does_not_try_to_delete_children_if_number_is_minimal():
    n = 5

    seen = set()

    initial = hbytes(list(hrange(n)))

    @shrinking_from(initial)
    def shrinker(data):
        good = True
        for i in hrange(n):
            data.start_example(1)
            if i != data.draw_bits(8):
                good = False
            data.stop_example()
        if good:
            data.mark_interesting()
        else:
            seen.add(hbytes(data.buffer))

    shrinker.adaptive_example_deletion()

    assert len(seen) == n
    assert hbytes(n) in seen
    for i in range(1, n):
        b = bytearray(initial)
        b[i] = 0
        assert hbytes(b) in seen


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
    @shrinking_from([1, 1, 1, 7])
    def shrinker(data):
        n = data.draw_bits(1)
        if n:
            data.draw_bits(1)
            data.draw_bits(1)
        if data.draw_bits(8) == 7:
            data.mark_interesting()
    shrinker.pandas_hack()
    assert list(shrinker.shrink_target.buffer) == [0, 7]
