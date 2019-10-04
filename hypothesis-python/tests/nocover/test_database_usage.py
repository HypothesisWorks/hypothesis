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

import os.path

import hypothesis.strategies as st
from hypothesis import assume, core, find, given, settings
from hypothesis.database import ExampleDatabase, InMemoryExampleDatabase
from hypothesis.errors import NoSuchExample, Unsatisfiable
from hypothesis.internal.compat import hbytes
from tests.common.utils import (
    all_values,
    checks_deprecated_behaviour,
    non_covering_examples,
)


def has_a_non_zero_byte(x):
    return any(hbytes(x))


@checks_deprecated_behaviour
def test_saves_incremental_steps_in_database():
    key = b"a database key"
    database = InMemoryExampleDatabase()
    find(
        st.binary(min_size=10),
        lambda x: has_a_non_zero_byte(x),
        settings=settings(database=database),
        database_key=key,
    )
    assert len(all_values(database)) > 1


@checks_deprecated_behaviour
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
        assert False


@checks_deprecated_behaviour
def test_trashes_invalid_examples():
    key = b"a database key"
    database = InMemoryExampleDatabase()
    finicky = False

    def stuff():
        try:
            find(
                st.binary(min_size=100),
                lambda x: assume(not finicky) and has_a_non_zero_byte(x),
                settings=settings(database=database),
                database_key=key,
            )
        except Unsatisfiable:
            pass

    stuff()
    original = len(all_values(database))
    assert original > 1
    finicky = True
    stuff()
    assert len(all_values(database)) < original


@checks_deprecated_behaviour
def test_respects_max_examples_in_database_usage():
    key = b"a database key"
    database = InMemoryExampleDatabase()
    do_we_care = True
    counter = [0]

    def check(x):
        counter[0] += 1
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

    stuff()
    assert len(all_values(database)) > 10
    do_we_care = False
    counter[0] = 0
    stuff()
    assert counter == [10]


def test_does_not_use_database_when_seed_is_forced(monkeypatch):
    monkeypatch.setattr(core, "global_force_seed", 42)
    database = InMemoryExampleDatabase()
    database.fetch = None

    @settings(database=database)
    @given(st.integers())
    def test(i):
        pass

    test()


@given(st.binary(), st.binary())
def test_database_not_created_when_not_used(tmp_path_factory, key, value):
    path = tmp_path_factory.mktemp("hypothesis") / "examples"
    assert not os.path.exists(str(path))
    database = ExampleDatabase(path)
    assert not list(database.fetch(key))
    assert not os.path.exists(str(path))
    database.save(key, value)
    assert os.path.exists(str(path))
    assert list(database.fetch(key)) == [value]
