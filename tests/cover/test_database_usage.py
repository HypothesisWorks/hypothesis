# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

import hypothesis.strategies as st
from hypothesis import find, assume, settings
from hypothesis.errors import NoSuchExample, Unsatisfiable
from hypothesis.database import SQLiteExampleDatabase


def test_saves_incremental_steps_in_database():
    key = b"a database key"
    database = SQLiteExampleDatabase(':memory:')
    find(
        st.binary(min_size=10), lambda x: any(x),
        settings=settings(database=database), database_key=key
    )
    assert len(set(database.fetch(key))) > 1


def test_clears_out_database_as_things_get_boring():
    key = b"a database key"
    database = SQLiteExampleDatabase(':memory:')
    do_we_care = True

    def stuff():
        try:
            find(
                st.binary(min_size=50), lambda x: do_we_care and any(x),
                settings=settings(database=database, max_examples=10),
                database_key=key
            )
        except NoSuchExample:
            pass
    stuff()
    assert len(set(database.fetch(key))) > 1
    do_we_care = False
    stuff()
    assert len(set(database.fetch(key))) > 0

    for _ in range(100):
        stuff()
        if not set(database.fetch(key)):
            break
    else:
        assert False


def test_trashes_all_invalid_examples():
    key = b"a database key"
    database = SQLiteExampleDatabase(':memory:')
    finicky = False

    def stuff():
        try:
            find(
                st.binary(min_size=100),
                lambda x: assume(not finicky) and any(x),
                settings=settings(database=database, timeout=5),
                database_key=key
            )
        except Unsatisfiable:
            pass
    stuff()
    assert len(set(database.fetch(key))) > 1
    finicky = True
    stuff()
    assert len(set(database.fetch(key))) == 0


def test_respects_max_examples_in_database_usage():
    key = b"a database key"
    database = SQLiteExampleDatabase(':memory:')
    do_we_care = True
    counter = [0]

    def check(x):
        counter[0] += 1
        return do_we_care and any(x)

    def stuff():
        try:
            find(
                st.binary(min_size=100), check,
                settings=settings(database=database, max_examples=10),
                database_key=key
            )
        except NoSuchExample:
            pass
    stuff()
    assert len(set(database.fetch(key))) > 10
    do_we_care = False
    counter[0] = 0
    stuff()
    assert counter == [10]
