from hypothesis.internal.utils.hashitanyway import HashItAnyway
from collections import namedtuple
from tests.common.descriptors import Descriptor
from tests.common import small_table
from hypothesis import given, Verifier
from hypothesis.settings import Settings
from copy import deepcopy
from hypothesis.searchstrategy import RandomWithSeed
from random import Random
from tests.common.mutate import mutate_slightly, mutate_maliciously


def hia(x):
    return HashItAnyway(x)


def test_respects_equality_of_ints():
    assert hia(1) == hia(1)
    assert hia(1) != hia(2)


def test_respects_equality_of_lists_of_ints():
    assert hia([1, 1]) == hia([1, 1])
    assert hia([1, 2]) == hia([1, 2])


def test_respects_equality_of_types():
    assert hia(int) == hia(int)
    assert hia(int) != hia(str)


def test_respects_equality_of_lists_of_types():
    assert hia([int, str]) == hia([int, str])
    assert hia([str, int]) != hia([int, str])


def test_hashes_lists_deterministically():
    assert hash(hia([int, str])) == hash(hia([int, str]))


class Foo():

    def __hash__(self):
        raise TypeError('Unhashable type Foo')


def test_can_use_non_iterable_non_hashables_as_a_dict_key():
    d = {}
    x = hia(Foo())
    d[x] = 1
    assert d[x] == 1
    y = hia(Foo())
    d[y] = 2
    assert d[x] == 1
    assert d[y] == 2


def test_can_use_old_style_class_objects_as_a_dict_key():
    d = {}
    x = hia(Foo)
    d[x] = 1
    assert d[x] == 1


def test_works_correctly_as_a_dict_key():
    k1 = hia([int, str])
    k2 = hia([int, str])
    d = {}
    d[k1] = 'hi'
    assert d[k2] == 'hi'
    d[k2] = 'bye'
    assert d[k1] == 'bye'
    assert len(d) == 1

Hi = namedtuple('Hi', ('a', 'b'))


def test_should_regard_named_tuples_as_distinct_from_unnamed():
    assert Hi(1, 2) == (1, 2)
    assert hia(Hi(1, 2)) != hia((1, 2))


def test_has_a_sensible_string_representation():
    x = str(hia('kittens'))
    assert 'HashItAnyway' in x
    assert 'kittens' in x


def test_hashing_random_with_seed():
    assert hia(
        RandomWithSeed(237230384214978941106830136598254622812)
    ) == hia(
        RandomWithSeed(237230384214978941106830136598254622812)
    )


@given([Descriptor], Random, verifier=Verifier(
    strategy_table=small_table,
    settings=Settings(
        max_examples=500,
        timeout=100
    )
))
def test_can_put_and_retrieve_descriptors_from_a_list(ds, r):
    ds += [mutate_slightly(r, d) for d in ds]
    ds += [mutate_maliciously(r, d) for d in ds]
    mapping = {}
    for d in ds:
        mapping[HashItAnyway(d)] = d
    for d in ds:
        assert mapping[HashItAnyway(deepcopy(d))] == d
