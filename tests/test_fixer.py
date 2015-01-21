from hypothesis.internal.utils.fixers import actually_equal, real_index
import random
import pytest


def test_lists_of_same_elements_are_equal():
    assert actually_equal([1, 2, 3], [1, 2, 3])


def test_lists_of_different_elements_are_not():
    assert not actually_equal([1, 2, 3], [1, 2, 4])


def test_lists_of_different_length_are_not():
    assert not actually_equal([1] * 3, [1] * 4)


def test_dicts_of_same_length_but_different_keys_are_not_equal():
    assert not actually_equal({1: 2}, {2: 1})


def test_sets_are_not_actually_equal_to_frozensets():
    assert not actually_equal(set(), frozenset())


def test_lists_of_sets_are_not_actually_equal_to_lists_of_frozensets():
    assert not actually_equal([set()], [frozenset()])


def test_an_object_is_actually_equal_to_itself():
    x = object()
    assert actually_equal(x, x)


def test_two_objects_are_not():
    assert not actually_equal(object(), object())


class Inclusive(object):

    def __eq__(self, other):
        return isinstance(other, Inclusive)

    def __ne__(self, other):
        return not self.__eq__(other)


def test_respects_equality_given_no_reason_not_to():
    assert actually_equal(Inclusive(), Inclusive())


def test_handles_ints_correctly():
    assert actually_equal(1, 1)
    assert not actually_equal(1, 2)


class LyingList(list):

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


def test_rejects_collections_which_lie_about_being_equal():
    assert not actually_equal(LyingList([1, 2, 3]), LyingList([1, 2]))


class WeirdSet(frozenset):
    pass


def test_rejects_equal_things_of_different_types():
    assert not actually_equal(WeirdSet(), frozenset())


def test_sets_are_equal_to_sets_correctly():
    assert actually_equal({1, 2, 3}, {3, 2, 1})
    assert not actually_equal({1, 2, 3}, {3, 2})
    assert not actually_equal({3, 2}, {1, 2, 3})
    assert not actually_equal({frozenset()}, {WeirdSet()})


def test_dicts_of_same_length_but_not_actually_equal_values_are_not_equal():
    assert actually_equal({1: 2}, {1: 2})
    assert not actually_equal({1: frozenset()}, {1: WeirdSet()})


class BrokenEqDict(dict):

    def __eq__(self, other):
        return isinstance(other, BrokenEqDict)

    def __ne__(self, other):
        return not self.__eq__(other)


def test_can_handle_really_broken_dicts():
    assert not actually_equal(
        BrokenEqDict({1: frozenset()}),
        BrokenEqDict({2: frozenset()})
    )


def test_handles_strings_correctly():
    s = hex(random.getrandbits(128))
    rs = ''.join(reversed(s))
    rrs = ''.join(reversed(rs))
    assert s is not rrs
    assert s == rrs, (rrs, s)
    assert actually_equal(s, rrs)


def test_actually_index_does_not_index_not_actually_equal_things():
    t = [frozenset()]
    with pytest.raises(ValueError):
        real_index(t, set())


def test_actually_index_can_index_past_an_inequal_thing():
    t = [frozenset(), set()]
    assert real_index(t, set()) == 1


def test_actually_index_can_use_real_index():
    t = [set()]
    assert real_index(t, set()) == 0
