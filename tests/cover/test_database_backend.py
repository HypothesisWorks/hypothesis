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

import base64

import pytest

from hypothesis import given, settings
from hypothesis.database import ExampleDatabase, SQLiteExampleDatabase, \
    InMemoryExampleDatabase, DirectoryBasedExampleDatabase
from hypothesis.strategies import lists, binary, tuples
from hypothesis.internal.compat import PY26, hrange

small_settings = settings(max_examples=100, timeout=4)

if PY26:
    # Workaround for bug with embedded null characters in a text string under
    # python 2.6
    alphabet = [chr(i) for i in hrange(1, 128)]
else:
    alphabet = None


@given(lists(tuples(binary(), binary())))
@small_settings
def test_backend_returns_what_you_put_in(xs):
    backend = SQLiteExampleDatabase(':memory:')
    mapping = {}
    for key, value in xs:
        mapping.setdefault(key, set()).add(value)
        backend.save(key, value)
    for key, values in mapping.items():
        backend_contents = list(backend.fetch(key))
        distinct_backend_contents = set(backend_contents)
        assert len(backend_contents) == len(distinct_backend_contents)
        assert distinct_backend_contents == set(values)


def test_does_not_commit_in_error_state():
    backend = SQLiteExampleDatabase(':memory:')
    backend.create_db_if_needed()
    try:
        with backend.cursor() as cursor:
            cursor.execute("""
                insert into hypothesis_data_mapping(key, value)
                values("a", "b")
            """)
            raise ValueError()
    except ValueError:
        pass

    assert list(backend.fetch(b'a')) == []


def test_can_double_close():
    backend = SQLiteExampleDatabase(':memory:')
    backend.create_db_if_needed()
    backend.close()
    backend.close()


def test_can_delete_keys():
    backend = SQLiteExampleDatabase(':memory:')
    backend.save(b'foo', b'bar')
    backend.save(b'foo', b'baz')
    backend.delete(b'foo', b'bar')
    assert list(backend.fetch(b'foo')) == [b'baz']


def test_ignores_badly_stored_values():
    backend = SQLiteExampleDatabase(':memory:')
    backend.create_db_if_needed()
    with backend.cursor() as cursor:
        cursor.execute("""
            insert into hypothesis_data_mapping(key, value)
            values(?, ?)
        """, (base64.b64encode(b'foo'), u'kittens'))
    assert list(backend.fetch(b'foo')) == []


def test_default_database_is_in_memory():
    assert isinstance(ExampleDatabase(), InMemoryExampleDatabase)


def test_default_on_disk_database_is_dir(tmpdir):
    assert isinstance(
        ExampleDatabase(tmpdir.join('foo')), DirectoryBasedExampleDatabase)


def test_selects_sqlite_database_if_name_matches(tmpdir):
    assert isinstance(
        ExampleDatabase(tmpdir.join('foo.db')), SQLiteExampleDatabase)
    assert isinstance(
        ExampleDatabase(tmpdir.join('foo.sqlite')), SQLiteExampleDatabase)
    assert isinstance(
        ExampleDatabase(tmpdir.join('foo.sqlite3')), SQLiteExampleDatabase)


def test_selects_directory_based_if_already_directory(tmpdir):
    path = str(tmpdir.join('hi.sqlite3'))
    DirectoryBasedExampleDatabase(path).save(b"foo", b"bar")
    assert isinstance(ExampleDatabase(path), DirectoryBasedExampleDatabase)


def test_selects_sqlite_if_already_sqlite(tmpdir):
    path = str(tmpdir.join('hi'))
    SQLiteExampleDatabase(path).save(b"foo", b"bar")
    assert isinstance(ExampleDatabase(path), SQLiteExampleDatabase)


def test_does_not_error_when_fetching_when_not_exist(tmpdir):
    db = DirectoryBasedExampleDatabase(tmpdir.join('examples'))
    db.fetch(b'foo')


@pytest.fixture(scope='function', params=['memory', 'sql', 'directory'])
def exampledatabase(request, tmpdir):
    if request.param == 'memory':
        return ExampleDatabase()
    if request.param == 'sql':
        return SQLiteExampleDatabase(str(tmpdir.join('example.db')))
    if request.param == 'directory':
        return DirectoryBasedExampleDatabase(str(tmpdir.join('examples')))
    assert False


def test_can_delete_a_key_that_is_not_present(exampledatabase):
    exampledatabase.delete(b'foo', b'bar')


def test_can_fetch_a_key_that_is_not_present(exampledatabase):
    assert list(exampledatabase.fetch(b'foo')) == []


def test_saving_a_key_twice_fetches_it_once(exampledatabase):
    exampledatabase.save(b'foo', b'bar')
    exampledatabase.save(b'foo', b'bar')
    assert list(exampledatabase.fetch(b'foo')) == [b'bar']


def test_can_close_a_database_without_touching_it(exampledatabase):
    exampledatabase.close()


def test_can_close_a_database_after_saving(exampledatabase):
    exampledatabase.save(b'foo', b'bar')


def test_class_name_is_in_repr(exampledatabase):
    assert type(exampledatabase).__name__ in repr(exampledatabase)
    exampledatabase.close()


def test_two_directory_databases_can_interact(tmpdir):
    path = str(tmpdir)
    db1 = DirectoryBasedExampleDatabase(path)
    db2 = DirectoryBasedExampleDatabase(path)
    db1.save(b'foo', b'bar')
    assert list(db2.fetch(b'foo')) == [b'bar']
    db2.save(b'foo', b'bar')
    db2.save(b'foo', b'baz')
    assert sorted(db1.fetch(b'foo')) == [b'bar', b'baz']
