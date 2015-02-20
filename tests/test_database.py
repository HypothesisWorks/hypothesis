# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from random import Random
from collections import Counter, namedtuple

import pytest
import hypothesis.params as params
import hypothesis.settings as hs
from hypothesis import Verifier, given
from tests.common import small_table
from hypothesis.database import ExampleDatabase
from hypothesis.descriptors import Just, one_of, sampled_from
from hypothesis.strategytable import StrategyTable
from tests.common.descriptors import DescriptorWithValue
from hypothesis.searchstrategy import JustStrategy, RandomWithSeed, \
    SearchStrategy
from hypothesis.internal.compat import text_type, binary_type, \
    integer_types
from hypothesis.database.backend import Backend, SQLiteBackend
from hypothesis.database.formats import Format
from hypothesis.database.converter import JustConverter, ConverterTable
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


AB = namedtuple('AB', ('a', 'b'))

data_examples = (
    (AB(int, int), AB(1, 2)),
    (int, 1),
    ((int,), (1,)),
    (complex, complex(1, 1)),
    ({int}, {1}),
    (text_type, ''),
    (binary_type, b''),
    (Random, RandomWithSeed(1)),
    (Just(frozenset({False})), frozenset({False})),
    (({str}, bool), (set(), True)),
    ({'\x9aLLLL\x1c': {bool}}, {'\x9aLLLL\x1c': {False}}),
    (one_of([int, str]), 1),
    ([
        [{int}],
        [[{int}]]],
        [[[]]]),
    (sampled_from(elements=(1,)), 1),
    (one_of(({1: int}, {1: bool})), {1: 2}),
    (one_of(({1: int}, {1: bool})), {1: False}),
    ({float}, {0.0460563451184767, -0.19420794805570227}),
)


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


@pytest.mark.parametrize(('descriptor', 'value', 'backend', 'format'), [
    dv + bf
    for dv in data_examples
    for bf in backend_format_pairs
])
def test_simple_example_set(descriptor, value, backend, format):
    run_round_trip(descriptor, value, backend=backend, format=format)


@given(DescriptorWithValue, verifier=Verifier(
    strategy_table=small_table,
    settings=hs.Settings(max_examples=500),
))
def test_can_round_trip_a_single_value_through_the_database(dav):
    run_round_trip(dav.descriptor, dav.value)


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


def test_storage_errors_if_given_the_wrong_type():
    database = ExampleDatabase()
    ints = database.storage_for(int)
    with pytest.raises(ValueError):
        ints.save('hi')


def test_storage_does_not_error_if_the_database_is_invalid():
    database = ExampleDatabase()
    ints = database.storage_for(int)
    database.backend.save(ints.key, '[false, false, true]')
    assert list(ints.fetch()) == []


class PickyStrategyLazyFormat(object):
    pass


def test_storage_does_not_return_things_not_matching_strategy():
    table = StrategyTable()
    strategy = JustStrategy(PickyStrategyLazyFormat())

    strategy.could_have_produced = lambda *args: False
    table.define_specification_for(
        PickyStrategyLazyFormat, lambda s, d: strategy
    )
    converters = ConverterTable(strategy_table=table)
    converters.define_specification_for(
        PickyStrategyLazyFormat,
        lambda s, d: JustConverter(PickyStrategyLazyFormat()))
    database = ExampleDatabase(
        converters=converters,
        backend=SQLiteBackend(),
    )
    stor = database.storage_for(PickyStrategyLazyFormat)
    database.backend.save(stor.key, 'null')
    assert list(database.backend.fetch(stor.key)) != []
    assert list(stor.fetch()) == []
    assert list(database.backend.fetch(stor.key)) == []


def test_storage_cleans_up_invalid_data_from_the_db():
    database = ExampleDatabase()
    ints = database.storage_for(int)
    database.backend.save(ints.key, '[false, false, true]')
    assert list(database.backend.fetch(ints.key)) != []
    assert list(ints.fetch()) == []
    assert list(database.backend.fetch(ints.key)) == []


class Awkward(str):
    pass

ConverterTable.default().mark_not_serializeable(Awkward)


class AwkwardStrategy(SearchStrategy):
    descriptor = Awkward
    parameter = params.CompositeParameter()

    def produce_template(self, random, pv):
        return Awkward()

StrategyTable.default().define_specification_for(
    Awkward,
    lambda s, d: AwkwardStrategy())


def test_can_verify_a_non_serializale_type():
    verifier = Verifier(settings=hs.Settings(database=ExampleDatabase()))
    verifier.falsify(lambda x: len(x) > 0, Awkward)


def test_verifier_deduplicates_on_coming_out_of_the_database():
    db = ExampleDatabase()
    storage = db.storage_for((frozenset({int}),))
    db.backend.save(storage.key, '[1, 2, 3]')
    db.backend.save(storage.key, '[3, 2, 1]')
    counter = Counter()
    calls = []
    good = frozenset({1, 2, 3})

    def count_and_object(x):
        counter[x] += 1
        if not calls:
            calls.append(x)
        return x == good

    verifier = Verifier(settings=hs.Settings(database=db))
    verifier.falsify(count_and_object, frozenset({int}))
    assert calls[0] == good
    assert counter[good] == 1


@given(text_type)
def test_can_save_all_strings(s):
    db = ExampleDatabase()
    storage = db.storage_for(text_type)
    storage.save(s)
