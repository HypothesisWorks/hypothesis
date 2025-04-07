# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import assume, core, find, given, settings, strategies as st
from hypothesis.database import (
    DirectoryBasedExampleDatabase,
    GitHubArtifactDatabase,
    InMemoryExampleDatabase,
    ReadOnlyDatabase,
)
from hypothesis.errors import NoSuchExample, Unsatisfiable
from hypothesis.internal.entropy import deterministic_PRNG

from tests.common.utils import (
    Why,
    all_values,
    non_covering_examples,
    xfail_on_crosshair,
)


def has_a_non_zero_byte(x):
    return any(bytes(x))


def test_saves_incremental_steps_in_database():
    key = b"a database key"
    database = InMemoryExampleDatabase()
    find(
        st.binary(min_size=10),
        has_a_non_zero_byte,
        settings=settings(database=database),
        database_key=key,
    )
    assert len(all_values(database)) > 1


@xfail_on_crosshair(Why.symbolic_outside_context, strict=False)
def test_clears_out_database_as_things_get_boring():
    key = b"a database key"
    database = InMemoryExampleDatabase()
    do_we_care = True

    def stuff():
        try:
            find(
                st.binary(min_size=50),
                lambda x: do_we_care and has_a_non_zero_byte(x),
                settings=settings(database=database, max_examples=10),
                database_key=key,
            )
        except NoSuchExample:
            pass

    stuff()
    assert len(non_covering_examples(database)) > 1
    do_we_care = False
    stuff()
    initial = len(non_covering_examples(database))
    assert initial > 0

    for _ in range(initial):
        stuff()
        keys = len(non_covering_examples(database))
        if not keys:
            break
    else:
        raise AssertionError


@xfail_on_crosshair(Why.other, strict=False)
def test_trashes_invalid_examples():
    key = b"a database key"
    database = InMemoryExampleDatabase()

    invalid = set()

    def stuff():
        try:

            def condition(x):
                assume(x not in invalid)
                return not invalid and has_a_non_zero_byte(x)

            return find(
                st.binary(min_size=5),
                condition,
                settings=settings(database=database),
                database_key=key,
            )
        except (Unsatisfiable, NoSuchExample):
            pass

    with deterministic_PRNG():
        value = stuff()

    original = len(all_values(database))
    assert original > 1

    invalid.add(value)
    with deterministic_PRNG():
        stuff()
    assert len(all_values(database)) < original


@pytest.mark.skipif(
    settings._current_profile == "crosshair",
    reason="condition is easy for crosshair, stops early",
)
def test_respects_max_examples_in_database_usage():
    key = b"a database key"
    database = InMemoryExampleDatabase()
    do_we_care = True
    counter = 0

    def check(x):
        nonlocal counter
        counter += 1
        return do_we_care and has_a_non_zero_byte(x)

    def stuff():
        try:
            find(
                st.binary(min_size=100),
                check,
                settings=settings(database=database, max_examples=10),
                database_key=key,
            )
        except NoSuchExample:
            pass

    with deterministic_PRNG():
        stuff()
    assert len(all_values(database)) > 10
    do_we_care = False
    counter = 0
    with deterministic_PRNG():
        stuff()
    assert counter == 10


def test_does_not_use_database_when_seed_is_forced(monkeypatch):
    monkeypatch.setattr(core, "global_force_seed", 42)
    database = InMemoryExampleDatabase()
    database.fetch = None  # type: ignore

    @settings(database=database)
    @given(st.integers())
    def test(i):
        pass

    test()


@given(st.binary(), st.binary())
def test_database_not_created_when_not_used(tmp_path_factory, key, value):
    path = tmp_path_factory.mktemp("hypothesis") / "examples"
    assert not path.exists()
    database = DirectoryBasedExampleDatabase(path)
    assert not list(database.fetch(key))
    assert not path.exists()
    database.save(key, value)
    assert path.exists()
    assert list(database.fetch(key)) == [value]


def test_ga_database_not_created_when_not_used(tmp_path_factory):
    path = tmp_path_factory.mktemp("hypothesis") / "github-actions"
    assert not path.exists()
    ReadOnlyDatabase(GitHubArtifactDatabase("mock", "mock", path=path))
    assert not path.exists()
