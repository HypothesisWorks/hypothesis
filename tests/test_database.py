from __future__ import unicode_literals

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
from hypothesis.internal.compat import text_type, binary_type


def test_deduplicates():
    database = ExampleDatabase()
    storage = database.storage_for(int)
    storage.save(1)
    storage.save(1)
    assert list(storage.fetch()) == [1]


def run_round_trip(descriptor, value):
    db = ExampleDatabase()
    storage = db.storage_for(descriptor)
    storage.save(value)
    saved = list(storage.fetch())
    assert saved == [value]


@pytest.mark.parametrize(('descriptor', 'value'), (
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
))
def test_simple_example_set(descriptor, value):
    run_round_trip(descriptor, value)


@given(DescriptorWithValue, verifier=Verifier(
    strategy_table=small_table,
    settings=hs.Settings(max_examples=500),
))
def test_can_round_trip_a_single_value_through_the_database(dav):
    run_round_trip(dav.descriptor, dav.value)


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
