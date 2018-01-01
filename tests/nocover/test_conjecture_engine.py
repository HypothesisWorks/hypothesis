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

from hypothesis import strategies as st
from hypothesis import HealthCheck, given, settings, unlimited
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.internal.compat import hbytes
from tests.cover.test_conjecture_engine import run_to_buffer, slow_shrinker
from hypothesis.internal.conjecture.engine import ConjectureRunner


@given(st.random_module())
@settings(max_shrinks=0, deadline=None, perform_health_check=False)
def test_lot_of_dead_nodes(rnd):
    @run_to_buffer
    def x(data):
        for i in range(5):
            if data.draw_bytes(1)[0] != i:
                data.mark_invalid()
        data.mark_interesting()
    assert x == hbytes([0, 1, 2, 3, 4])


def test_saves_data_while_shrinking():
    key = b'hi there'
    n = 5
    db = InMemoryExampleDatabase()
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
    assert runner.interesting_examples
    assert len(seen) == n
    in_db = set(
        v
        for vs in db.data.values()
        for v in vs
    )
    assert in_db.issubset(seen)
    assert in_db == seen


@given(st.randoms(), st.random_module())
@settings(
    max_shrinks=0, deadline=None, suppress_health_check=[HealthCheck.hung_test]
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


def test_garbage_collects_the_database():
    key = b'hi there'
    n = 200
    db = InMemoryExampleDatabase()

    local_settings = settings(
        database=db, max_shrinks=n, timeout=unlimited)

    runner = ConjectureRunner(
        slow_shrinker(), settings=local_settings, database_key=key)
    runner.run()
    assert runner.interesting_examples

    def in_db():
        return set(
            v
            for vs in db.data.values()
            for v in vs
        )

    assert len(in_db()) == n + 1
    runner = ConjectureRunner(
        lambda data: data.draw_bytes(4),
        settings=local_settings, database_key=key)
    runner.run()
    assert 0 < len(in_db()) < n


def test_can_discard():
    n = 32

    @run_to_buffer
    def x(data):
        seen = set()
        while len(seen) < n:
            seen.add(hbytes(data.draw_bytes(1)))
        data.mark_interesting()
    assert len(x) == n
