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

from hypothesis import strategies as st
from hypothesis import Phase, given, settings, unlimited
from tests.common.utils import all_values, checks_deprecated_behaviour
from hypothesis.database import ExampleDatabase, InMemoryExampleDatabase
from hypothesis.internal.compat import hbytes, hrange, int_from_bytes, \
    bytes_from_list
from hypothesis.internal.conjecture.data import Status, ConjectureData
from hypothesis.internal.conjecture.engine import ConjectureRunner

MAX_SHRINKS = 2000


def run_to_buffer(f):
    runner = ConjectureRunner(f, settings=settings(
        max_examples=5000, max_iterations=10000, max_shrinks=MAX_SHRINKS,
        buffer_size=1024,
        database=None,
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
    assert x == bytes_from_list([0] * 9 + [1]) * 2


def test_clone_into_variable_draws():
    @run_to_buffer
    def x(data):
        small = 0
        large = 0
        for _ in range(30):
            data.start_example()
            b = data.draw_bytes(1)[0] & 1
            if b:
                data.draw_bytes(3)
                large += 1
            else:
                data.draw_bytes(2)
                small += 1
            data.stop_example()
        if small < 10:
            data.mark_invalid()
        if large >= 10:
            data.mark_interesting()
    assert set(x) == set((0, 1))
    assert x.count(1) == 10
    assert len(x) == 30 + (20 * 2) + (10 * 3)


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
    last = [None]

    def accept(data):
        x = data.draw_bytes(100)
        if x == last[0]:
            data.mark_interesting()
        l = last[0]
        if l is None:
            if all(x):
                last[0] = x
                data.mark_interesting()
            else:
                return
        diffs = [i for i in hrange(len(x)) if x[i] != l[i]]
        if len(diffs) == 1:
            i = diffs[0]
            if x[i] + 1 == l[i]:
                last[0] = x
                data.mark_interesting()
    return accept


@pytest.mark.parametrize('n', [1, 10, 100, 200])
def test_terminates_shrinks(n):
    db = ExampleDatabase(':memory:')
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
    l = draw_list(ConjectureData.for_buffer(b))
    assert len(l) == 1
    assert len(l[0]) == 1


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
        database=db,
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


@given(st.random_module())
@settings(
    max_shrinks=0, min_satisfying_examples=1, max_examples=2, deadline=None
)
def test_interleaving_engines(rnd):
    @run_to_buffer
    def x(data):
        rnd = Random(hbytes(data.draw_bytes(8)))

        def g(d2):
            while True:
                b = d2.draw_bytes(1)[0]
                result = data.draw_bytes(b)
                if 255 in result:
                    d2.mark_interesting()
                if 0 in result:
                    d2.mark_invalid()
        runner = ConjectureRunner(g, random=rnd)
        runner.run()
        if runner.last_data.status == Status.INTERESTING:
            data.mark_interesting()
    assert x[8:].count(255) == 1


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


def test_saves_data_while_shrinking():
    key = b'hi there'
    n = 5
    db = ExampleDatabase(':memory:')
    assert list(db.fetch(key)) == []
    seen = set()

    def f(data):
        x = data.draw_bytes(512)
        if sum(x) >= 5000 and len(seen) < n:
            seen.add(hbytes(x))
        if hbytes(x) in seen:
            data.mark_interesting()
    runner = ConjectureRunner(
        f, settings=settings(database=db), database_key=key)
    runner.run()
    assert runner.last_data.status == Status.INTERESTING
    assert len(seen) == n
    in_db = set(
        v
        for vs in db.data.values()
        for v in vs
    )
    assert in_db.issubset(seen)
    assert in_db == seen


def test_can_discard():
    n = 32

    @run_to_buffer
    def x(data):
        seen = set()
        while len(seen) < n:
            seen.add(hbytes(data.draw_bytes(1)))
        data.mark_interesting()
    assert len(x) == n


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


def test_garbage_collects_the_database():
    key = b'hi there'
    n = 200
    db = ExampleDatabase(':memory:')

    local_settings = settings(
        database=db, max_shrinks=n, timeout=unlimited)

    runner = ConjectureRunner(
        slow_shrinker(), settings=local_settings, database_key=key)
    runner.run()
    assert runner.last_data.status == Status.INTERESTING

    def in_db():
        return set(
            v
            for vs in db.data.values()
            for v in vs
        )

    assert len(in_db()) == n + 1
    runner = ConjectureRunner(
        lambda data: None, settings=local_settings, database_key=key)
    runner.run()
    assert 0 < len(in_db()) < n


@given(st.randoms(), st.random_module())
@settings(max_shrinks=0)
def test_maliciously_bad_generator(rnd, seed):
    @run_to_buffer
    def x(data):
        for _ in range(rnd.randint(1, 100)):
            data.draw_bytes(rnd.randint(1, 10))
        if rnd.randint(0, 1):
            data.mark_invalid()
        else:
            data.mark_interesting()


@given(st.random_module())
def test_lot_of_dead_nodes(rnd):
    @run_to_buffer
    def x(data):
        for i in range(5):
            if data.draw_bytes(1)[0] != i:
                data.mark_invalid()
        data.mark_interesting()
    assert x == hbytes([0, 1, 2, 3, 4])


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


def test_fully_exhaust_base():
    """In this test we generate all possible values for the first byte but
    never get to the point where we exhaust the root of the tree."""
    seed_random(0)

    seen = set()

    def f(data):
        seen.add(data.draw_bytes(2))

    runner = ConjectureRunner(f, settings=settings(
        max_examples=10000, max_iterations=10000, max_shrinks=MAX_SHRINKS,
        buffer_size=1024,
        database=None,
    ))
    runner.run()
    assert len(seen) > 256
    assert len({x[0] for x in seen}) == 256


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
    seen = [hbytes([255] * 4)]

    def tagged(data):
        seen[0] = min(seen[0], hbytes(data.draw_bytes(4)))
        data.add_tag(0)

    db = InMemoryExampleDatabase()
    runner = ConjectureRunner(tagged, settings=settings(
        max_examples=100, max_iterations=10000, max_shrinks=0,
        buffer_size=1024,
        database=db,
    ), database_key=b'stuff')
    runner.run()
    assert all_values(db) == set(seen)


def test_can_cover_without_a_database_key():
    def tagged(data):
        data.add_tag(0)

    runner = ConjectureRunner(tagged, settings=settings(), database_key=None)
    runner.run()
    assert len(runner.covering_examples) == 1
