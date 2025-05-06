# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import itertools

import pytest

from hypothesis import HealthCheck, Phase, settings, strategies as st
from hypothesis.database import (
    InMemoryExampleDatabase,
    choices_from_bytes,
    choices_to_bytes,
)
from hypothesis.internal.conjecture.data import Status
from hypothesis.internal.conjecture.engine import ConjectureRunner, RunIsComplete
from hypothesis.internal.entropy import deterministic_PRNG

from tests.conjecture.common import interesting_origin


def test_pareto_front_contains_different_interesting_reasons():
    with deterministic_PRNG():

        def test(data):
            data.target_observations[""] = 1
            n = data.draw_integer(0, 2**4 - 1)
            data.mark_interesting(interesting_origin(n))

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


def test_pareto_front_omits_invalid_examples():
    with deterministic_PRNG():

        def test(data):
            x = data.draw_integer(0, 2**4 - 1)
            if x % 2:
                data.target_observations[""] = 1
                data.mark_invalid()

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

        assert len(runner.pareto_front) == 0


def test_database_contains_only_pareto_front():
    with deterministic_PRNG():

        def test(data):
            data.target_observations["1"] = data.draw(st.integers(0, 2**4))
            data.draw(st.integers(0, 2**64))
            data.target_observations["2"] = data.draw(st.integers(0, 2**8))

            assert len(set(db.fetch(b"stuff.pareto"))) == len(runner.pareto_front)

        db = InMemoryExampleDatabase()
        runner = ConjectureRunner(
            test,
            settings=settings(
                max_examples=500, database=db, suppress_health_check=list(HealthCheck)
            ),
            database_key=b"stuff",
        )
        runner.run()

        assert len(runner.pareto_front) <= 500
        for v in runner.pareto_front:
            assert v.status >= Status.VALID

        values = set(db.fetch(b"stuff.pareto"))
        assert len(values) == len(runner.pareto_front), {
            choices_to_bytes(data.choices) for data in runner.pareto_front
        }.symmetric_difference(values)

        for data in runner.pareto_front:
            assert choices_to_bytes(data.choices) in values
            assert data in runner.pareto_front

        for b in values:
            choices = choices_from_bytes(b)
            assert runner.cached_test_function(choices) in runner.pareto_front


def test_clears_defunct_pareto_front():
    with deterministic_PRNG():

        def test(data):
            data.target_observations[""] = 1
            data.draw_integer(0, 2**8 - 1)
            data.draw_integer(0, 2**8 - 1)

        db = InMemoryExampleDatabase()

        runner = ConjectureRunner(
            test,
            settings=settings(
                max_examples=10000,
                database=db,
                suppress_health_check=list(HealthCheck),
                phases=[Phase.reuse],
            ),
            database_key=b"stuff",
        )

        for i in range(256):
            db.save(runner.pareto_key, choices_to_bytes((i, 0)))

        runner.run()

        assert len(list(db.fetch(runner.pareto_key))) == 1


def test_down_samples_the_pareto_front():
    with deterministic_PRNG():

        def test(data):
            data.draw_integer(0, 2**8 - 1)
            data.draw_integer(0, 2**8 - 1)

        db = InMemoryExampleDatabase()

        runner = ConjectureRunner(
            test,
            settings=settings(
                max_examples=1000,
                database=db,
                suppress_health_check=list(HealthCheck),
                phases=[Phase.reuse],
            ),
            database_key=b"stuff",
        )

        for n1, n2 in itertools.product(range(256), range(256)):
            db.save(runner.pareto_key, choices_to_bytes((n1, n2)))

        with pytest.raises(RunIsComplete):
            runner.reuse_existing_examples()

        assert runner.valid_examples == 1000


def test_stops_loading_pareto_front_if_interesting():
    with deterministic_PRNG():

        def test(data):
            data.draw_integer()
            data.draw_integer()
            data.mark_interesting()

        db = InMemoryExampleDatabase()

        runner = ConjectureRunner(
            test,
            settings=settings(
                max_examples=1000,
                database=db,
                suppress_health_check=list(HealthCheck),
                phases=[Phase.reuse],
            ),
            database_key=b"stuff",
        )

        for n1, n2 in itertools.product(range(256), range(256)):
            db.save(runner.pareto_key, choices_to_bytes((n1, n2)))

        runner.reuse_existing_examples()

        assert runner.call_count == 1


def test_uses_tags_in_calculating_pareto_front():
    with deterministic_PRNG():

        def test(data):
            data.target_observations[""] = 1
            if data.draw_boolean():
                data.start_span(11)
                data.draw_integer(0, 2**8 - 1)
                data.stop_span()

        runner = ConjectureRunner(
            test,
            settings=settings(max_examples=10, database=InMemoryExampleDatabase()),
            database_key=b"stuff",
        )

        runner.run()

        assert len(runner.pareto_front) == 2


def test_optimises_the_pareto_front():
    def test(data):
        count = 0
        while data.draw_integer(0, 2**8 - 1):
            count += 1

        data.target_observations[""] = min(count, 5)

    runner = ConjectureRunner(
        test,
        settings=settings(max_examples=10000, database=InMemoryExampleDatabase()),
        database_key=b"stuff",
    )
    runner.cached_test_function([255] * 20 + [0])
    runner.pareto_optimise()

    assert len(runner.pareto_front) == 6
    for i, data in enumerate(runner.pareto_front):
        assert data.choices == (1,) * i + (0,)


def test_does_not_optimise_the_pareto_front_if_interesting():
    def test(data):
        n = data.draw_integer(0, 2**8 - 1)
        data.target_observations[""] = n
        if n == 255:
            data.mark_interesting()

    runner = ConjectureRunner(
        test,
        settings=settings(max_examples=10000, database=InMemoryExampleDatabase()),
        database_key=b"stuff",
    )

    runner.cached_test_function([0])
    runner.pareto_optimise = None
    runner.optimise_targets()

    assert runner.interesting_examples


def test_stops_optimising_once_interesting():
    hi = 2**16 - 1

    def test(data):
        n = data.draw_integer(0, 2**16 - 1)
        data.target_observations[""] = n
        if n < hi:
            data.mark_interesting()

    runner = ConjectureRunner(
        test,
        settings=settings(max_examples=10000, database=InMemoryExampleDatabase()),
        database_key=b"stuff",
    )

    data = runner.cached_test_function([hi])
    assert data.status == Status.VALID
    runner.pareto_optimise()
    assert runner.call_count <= 20
    assert runner.interesting_examples
