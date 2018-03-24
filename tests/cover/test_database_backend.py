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

import os

import pytest

from hypothesis import given, settings
from hypothesis.database import ExampleDatabase, InMemoryExampleDatabase, \
    DirectoryBasedExampleDatabase
from hypothesis.strategies import lists, binary, tuples

small_settings = settings(max_examples=50)


@given(lists(tuples(binary(), binary())))
@small_settings
def test_backend_returns_what_you_put_in(xs):
    backend = InMemoryExampleDatabase()
    mapping = {}
    for key, value in xs:
        mapping.setdefault(key, set()).add(value)
        backend.save(key, value)
    for key, values in mapping.items():
        backend_contents = list(backend.fetch(key))
        distinct_backend_contents = set(backend_contents)
        assert len(backend_contents) == len(distinct_backend_contents)
        assert distinct_backend_contents == set(values)


def test_can_delete_keys():
    backend = InMemoryExampleDatabase()
    backend.save(b'foo', b'bar')
    backend.save(b'foo', b'baz')
    backend.delete(b'foo', b'bar')
    assert list(backend.fetch(b'foo')) == [b'baz']


def test_default_database_is_in_memory():
    assert isinstance(ExampleDatabase(), InMemoryExampleDatabase)


def test_default_on_disk_database_is_dir(tmpdir):
    assert isinstance(
        ExampleDatabase(tmpdir.join('foo')), DirectoryBasedExampleDatabase)


def test_selects_directory_based_if_already_directory(tmpdir):
    path = str(tmpdir.join('hi.sqlite3'))
    DirectoryBasedExampleDatabase(path).save(b'foo', b'bar')
    assert isinstance(ExampleDatabase(path), DirectoryBasedExampleDatabase)


def test_does_not_error_when_fetching_when_not_exist(tmpdir):
    db = DirectoryBasedExampleDatabase(tmpdir.join('examples'))
    db.fetch(b'foo')


@pytest.fixture(scope='function', params=['memory', 'directory'])
def exampledatabase(request, tmpdir):
    if request.param == 'memory':
        return ExampleDatabase()
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


def test_an_absent_value_is_present_after_it_moves(exampledatabase):
    exampledatabase.move(b'a', b'b', b'c')
    assert next(exampledatabase.fetch(b'b')) == b'c'


def test_an_absent_value_is_present_after_it_moves_to_self(exampledatabase):
    exampledatabase.move(b'a', b'a', b'b')
    assert next(exampledatabase.fetch(b'a')) == b'b'


def test_two_directory_databases_can_interact(tmpdir):
    path = str(tmpdir)
    db1 = DirectoryBasedExampleDatabase(path)
    db2 = DirectoryBasedExampleDatabase(path)
    db1.save(b'foo', b'bar')
    assert list(db2.fetch(b'foo')) == [b'bar']
    db2.save(b'foo', b'bar')
    db2.save(b'foo', b'baz')
    assert sorted(db1.fetch(b'foo')) == [b'bar', b'baz']


def test_can_handle_disappearing_files(tmpdir, monkeypatch):
    path = str(tmpdir)
    db = DirectoryBasedExampleDatabase(path)
    db.save(b'foo', b'bar')
    base_listdir = os.listdir
    monkeypatch.setattr(os, 'listdir',
                        lambda d: base_listdir(d) + ['this-does-not-exist'])
    assert list(db.fetch(b'foo')) == [b'bar']
