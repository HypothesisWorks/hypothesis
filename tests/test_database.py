# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
import hypothesis.settings as hs
from hypothesis import Verifier, given
from tests.common import small_table
from hypothesis.database import ExampleDatabase
from tests.common.descriptors import DescriptorWithValue
from hypothesis.internal.compat import text_type, integer_types
from hypothesis.database.backend import Backend, SQLiteBackend
from hypothesis.database.formats import Format, JSONFormat
from hypothesis.internal.utils.fixers import actually_equal


def test_deduplicates():
    database = ExampleDatabase()
    storage = database.storage_for(int)
    storage.save(1)
    storage.save(1)
    assert list(storage.fetch()) == [1]


def run_round_trip(descriptor, value, format=None, backend=None):
    if backend is not None:
        backend = backend()
    else:
        backend = SQLiteBackend()
    db = ExampleDatabase(format=format, backend=backend)
    storage = db.storage_for(descriptor)
    storage.save(value)
    saved = list(storage.fetch())
    assert actually_equal(saved, [value])


class InMemoryBackend(Backend):

    def __init__(self):
        self.data = {}

    def data_type(self):
        return object

    def save(self, key, value):
        self.data.setdefault(key, set()).add(value)

    def fetch(self, key):
        for v in self.data.get(key, ()):
            yield v


class ObjectFormat(Format):

    def data_type(self):
        return object

    def serialize_basic(self, value):
        if isinstance(value, list):
            return tuple(
                map(self.serialize_basic, value)
            )
        else:
            assert value is None or isinstance(
                value,
                (bool, float, text_type) + integer_types
            )
            return value

    def deserialize_data(self, data):
        if isinstance(data, tuple):
            return list(
                map(self.deserialize_data, data)
            )
        else:
            return data

backend_format_pairs = (
    (SQLiteBackend, None),
    (InMemoryBackend, ObjectFormat()),
)


@given(DescriptorWithValue, verifier=Verifier(
    strategy_table=small_table,
    settings=hs.Settings(max_examples=500),
))
def test_can_round_trip_a_single_value_through_the_database(dav):
    run_round_trip(dav.descriptor, dav.template)


def test_errors_if_given_incompatible_format_and_backend():
    with pytest.raises(ValueError):
        ExampleDatabase(
            backend=InMemoryBackend()
        )


def test_a_verifier_saves_any_failing_examples_in_its_database():
    database = ExampleDatabase()
    verifier = Verifier(settings=hs.Settings(database=database))
    counterexample = verifier.falsify(lambda x: x > 0, int)
    saved = list(database.storage_for((int,)).fetch())
    assert saved == [counterexample]


def test_a_verifier_retrieves_previous_failing_examples_from_the_database():
    database = ExampleDatabase()
    verifier = Verifier(settings=hs.Settings(database=database))
    verifier.falsify(lambda x: x < 11, int)
    called = []

    def save_calls(t):
        called.append(t)
        return False

    verifier2 = Verifier(settings=hs.Settings(database=database))
    verifier2.falsify(save_calls, int)
    assert called[0] == 11
    assert all(0 <= x <= 11 for x in called)


def test_a_verifier_can_still_do_its_thing_if_a_saved_example_fails():
    database = ExampleDatabase()
    verifier = Verifier(settings=hs.Settings(database=database))
    verifier.falsify(lambda x: x < 11, int)
    verifier2 = Verifier(settings=hs.Settings(database=database))
    verifier2.falsify(lambda x: x < 100, int)


def test_storage_does_not_error_if_the_database_is_invalid():
    database = ExampleDatabase()
    ints = database.storage_for(int)
    database.backend.save(ints.key, '["hi", "there"]')
    assert list(ints.fetch()) == []


class PickyStrategyLazyFormat(object):
    pass


def test_storage_cleans_up_invalid_data_from_the_db():
    database = ExampleDatabase()
    ints = database.storage_for(int)
    database.backend.save(ints.key, '[false, false, true]')
    assert list(database.backend.fetch(ints.key)) != []
    assert list(ints.fetch()) == []
    assert list(database.backend.fetch(ints.key)) == []


@given(text_type)
def test_can_save_all_strings(s):
    db = ExampleDatabase()
    storage = db.storage_for(text_type)
    storage.save(tuple(s))


def test_db_has_path_in_repr():
    backend = SQLiteBackend(':memory:')
    db = ExampleDatabase(backend=backend)
    assert ':memory:' in repr(db)


def test_storage_has_descriptor_in_repr():
    db = ExampleDatabase()
    d = (int, int)
    s = db.storage_for(d)
    assert repr(d) in repr(s)


def test_json_format_repr_is_nice():
    assert repr(JSONFormat()) == 'JSONFormat()'
