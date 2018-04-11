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

import pytest

import hypothesis.strategies as st
from hypothesis import Verbosity, core, find, given, assume, settings, \
    unlimited
from hypothesis.errors import NoSuchExample, Unsatisfiable
from tests.common.utils import all_values, non_covering_examples
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.internal.compat import hbytes


def has_a_non_zero_byte(x):
    return any(hbytes(x))


def test_saves_incremental_steps_in_database():
    key = b'a database key'
    database = InMemoryExampleDatabase()
    find(
        st.binary(min_size=10), lambda x: has_a_non_zero_byte(x),
        settings=settings(database=database), database_key=key
    )
    assert len(all_values(database)) > 1


def test_clears_out_database_as_things_get_boring():
    key = b'a database key'
    database = InMemoryExampleDatabase()
    do_we_care = True

    def stuff():
        try:
            find(
                st.binary(min_size=50),
                lambda x: do_we_care and has_a_non_zero_byte(x),
                settings=settings(database=database, max_examples=10),
                database_key=key
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


def test_trashes_invalid_examples():
    key = b'a database key'
    database = InMemoryExampleDatabase()
    finicky = False

    def stuff():
        try:
            find(
                st.binary(min_size=100),
                lambda x: assume(not finicky) and has_a_non_zero_byte(x),
                settings=settings(database=database, max_shrinks=10),
                database_key=key
            )
        except Unsatisfiable:
            pass
    stuff()
    original = len(all_values(database))
    assert original > 1
    finicky = True
    stuff()
    assert len(all_values(database)) < original


def test_respects_max_examples_in_database_usage():
    key = b'a database key'
    database = InMemoryExampleDatabase()
    do_we_care = True
    counter = [0]

    def check(x):
        counter[0] += 1
        return do_we_care and has_a_non_zero_byte(x)

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
    assert len(all_values(database)) > 10
    do_we_care = False
    counter[0] = 0
    stuff()
    assert counter == [10]


def test_clears_out_everything_smaller_than_the_interesting_example():
    target = None

    # We retry the test run a few times to get a large enough initial
    # set of examples that we're not going to explore them all in the
    # initial run.
    last_sum = [None]

    database = InMemoryExampleDatabase()

    seen = set()

    @settings(
        database=database, verbosity=Verbosity.quiet, max_examples=100,
        timeout=unlimited, max_shrinks=100
    )
    @given(st.binary(min_size=10, max_size=10))
    def test(b):
        if target is not None:
            if len(seen) < 30:
                seen.add(b)
            if b in seen:
                return
            if b >= target:
                raise ValueError()
            return
        b = hbytes(b)
        s = sum(b)
        if (
            (last_sum[0] is None and s > 1000) or
            (last_sum[0] is not None and s >= last_sum[0] - 1)
        ):
            last_sum[0] = s
            raise ValueError()

    with pytest.raises(ValueError):
        test()

    saved = non_covering_examples(database)
    assert len(saved) > 30

    target = sorted(saved)[len(saved) // 2]

    with pytest.raises(ValueError):
        test()

    saved = non_covering_examples(database)
    assert target in saved or target in seen

    for s in saved:
        assert s >= target


def test_does_not_use_database_when_seed_is_forced(monkeypatch):
    monkeypatch.setattr(core, 'global_force_seed', 42)
    database = InMemoryExampleDatabase()
    database.fetch = None

    @settings(database=database)
    @given(st.integers())
    def test(i):
        pass

    test()
