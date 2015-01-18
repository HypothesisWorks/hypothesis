from __future__ import unicode_literals

from hypothesis.database.backend import Backend
from hypothesis.database.formats import Format
from hypothesis.database import ExampleDatabase
from hypothesis.database.converter import ConverterTable
from hypothesis.searchstrategy import RandomWithSeed
from hypothesis.descriptors import Just, one_of, sampled_from
from random import Random
from tests.common.descriptors import DescriptorWithValue
from tests.common import small_table
from hypothesis import given, Verifier
import pytest
import hypothesis.settings as hs
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.strategytable import StrategyTable
import hypothesis.params as params
from hypothesis.internal.compat import text_type, binary_type, integer_types


def test_deduplicates():
    database = ExampleDatabase()
    storage = database.storage_for(int)
    storage.save(1)
    storage.save(1)
    assert list(storage.fetch()) == [1]


def run_round_trip(descriptor, value, format=None, backend=None):
    db = ExampleDatabase(format=format, backend=backend)
    storage = db.storage_for(descriptor)
    storage.save(value)
    saved = list(storage.fetch())
    assert saved == [value]

data_examples = (
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
    (None, None),
    (InMemoryBackend(), ObjectFormat()),
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


def test_storage_errors_if_the_database_is_invalid():
    database = ExampleDatabase()
    ints = database.storage_for(int)
    database.backend.save(ints.key, '[false, false, true]')
    with pytest.raises(ValueError):
        list(ints.fetch())


class Awkward(str):
    pass

ConverterTable.default().mark_not_serializeable(Awkward)


class AwkwardStrategy(SearchStrategy):
    descriptor = Awkward
    parameter = params.CompositeParameter()

    def produce(self, random, pv):
        return Awkward()

StrategyTable.default().define_specification_for(
    Awkward,
    lambda s, d: AwkwardStrategy())


def test_can_verify_a_non_serializale_type():
    verifier = Verifier(settings=hs.Settings(database=ExampleDatabase()))
    verifier.falsify(lambda x: len(x) > 0, Awkward)
