from hypothesis.database import ExampleDatabase
from hypothesis.searchstrategy import RandomWithSeed
from hypothesis.descriptors import Just, one_of
from random import Random
from tests.common.descriptors import DescriptorWithValue
from tests.common import small_table
from hypothesis import given, Verifier
import pytest
import hypothesis.settings as hs


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


@pytest.mark.parametrize(("descriptor", "value"), (
    (int, 1),
    ((int,), (1,)),
    (complex, complex(1, 1)),
    ({int}, {1}),
    (str, ''),
    (Random, RandomWithSeed(1)),
    (Just(frozenset({False})), frozenset({False})),
    (({str}, bool), (set(), True)),
    ({'\x9aLLLL\x1c': {bool}}, {'\x9aLLLL\x1c': {False}}),
    (one_of([int, str]), 1),
    ([
        [{int}],
        [[{int}]]],
        [[[]]]),
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
