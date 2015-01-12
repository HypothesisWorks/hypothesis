from hypothesis.internal.utils.hashitanyway import HashItAnyway
from collections import namedtuple


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
