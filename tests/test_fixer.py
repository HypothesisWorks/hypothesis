# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import random

import pytest
from hypothesis import Verifier, given
from tests.common import small_table, small_verifier
from tests.common.mutate import mutate_slightly
from tests.common.descriptors import Descriptor
from hypothesis.internal.compat import hrange, text_type
from hypothesis.internal.utils.fixers import real_index, actually_equal


def test_lists_of_same_elements_are_equal():
    assert actually_equal([1, 2, 3], [1, 2, 3])


def test_lists_of_different_elements_are_not():
    assert not actually_equal([1, 2, 3], [1, 2, 4])


def test_lists_of_different_length_are_not():
    assert not actually_equal([1] * 3, [1] * 4)


def test_dicts_of_same_length_but_different_keys_are_not_equal():
    assert not actually_equal({1: 2}, {2: 1})


def test_dicts_of_different_length_are_not_equal():
    assert not actually_equal({1: 2}, {1: 2, 3: 4})


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
    s = text_type(hex(random.getrandbits(128)))
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


def test_fuzzy_equal_uses_full_repr_precision():
    assert not actually_equal(
        1113142313206.0,
        1113142313208.0,
        fuzzy=True,
    )


@given(float)
def test_a_float_is_fuzzy_equal_to_parsing_its_string(x):
    assert actually_equal(x, float(repr(x)), fuzzy=True)


@given(complex)
def test_a_complex_is_fuzzy_equal_to_parsing_its_string(x):
    assert actually_equal(x, complex(repr(x)), fuzzy=True)


@given(Descriptor, random.Random, verifier=small_verifier)
def test_equality_is_symmetric(d, r):
    test_cases = [d]
    for _ in hrange(10):
        test_cases.append(mutate_slightly(r, d))
    for x in test_cases:
        for y in test_cases:
            if actually_equal(x, y):
                assert actually_equal(y, x)


@given(Descriptor, random.Random, verifier=small_verifier)
def test_equality_is_transitive(d, r):
    test_cases = [d]
    for _ in hrange(10):
        test_cases.append(mutate_slightly(r, d))
    for x in test_cases:
        for y in test_cases:
            if actually_equal(x, y):
                for z in test_cases:
                    if actually_equal(y, z):
                        assert actually_equal(x, z)


def type_shape(x):
    if isinstance(x, dict):
        return (
            dict, {
                k: type_shape(v)
                for k, v in x.items()
            }
        )

    if isinstance(x, (frozenset, set)):
        return (
            type(x),
            type(x)(map(type_shape, x))
        )

    it = None
    try:
        it = iter(x)
    except TypeError:
        pass

    if it is not None:
        return (
            type(x),
            tuple(map(type_shape, it))
        )
    else:
        return type(x)


def test_type_shape_self_checks():
    assert type_shape(1) == int
    assert type_shape((1, 1.0)) == (tuple, (int, float))
    assert type_shape({1, 2}) == (set, {int})
    assert type_shape(frozenset({1, 2})) == (frozenset, frozenset({int}))
    assert type_shape({1: {2}}) == (
        dict, {1: (set, {int})})


@given(Descriptor, random.Random, verifier=Verifier(
    strategy_table=small_table,
))
def test_actually_equal_things_have_same_type_shape(d, r):
    for _ in hrange(10):
        d2 = mutate_slightly(r, d)
        if actually_equal(d, d2):
            assert type_shape(d) == type_shape(d2)


class BadCollection(object):

    def __init__(self, *values):
        self.values = values

    def __iter__(self):
        return iter(self.values)


def test_with_no_equality_different_length_is_still_not_equal():
    assert not actually_equal(BadCollection(1), BadCollection(1, 2))


def test_can_handle_collections_that_define_no_equality():
    assert actually_equal(
        BadCollection(1, 2, 3),
        BadCollection(1, 2, 3),
    )

    assert not actually_equal(
        BadCollection(1, 2, 3),
        BadCollection(1, 2, 4),
    )


class BadCollectionWithLength(BadCollection):

    def __init__(self, *values):
        self.values = values

    def __iter__(self):
        raise ValueError()

    def __len__(self):
        return len(self.values)


def test_uses_length_when_present():
    assert not actually_equal(
        BadCollectionWithLength(1), BadCollectionWithLength(1, 2))


class GoodCollectionWithLength(BadCollection):

    def __init__(self, *values):
        self.values = values

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)


def test_when_len_and_iter_present_and_len_equal_uses_iter():
    assert actually_equal(
        GoodCollectionWithLength(1, 2),
        GoodCollectionWithLength(1, 2),
    )


def test_equal_complex_are_fuzzy_equal():
    x = -43j
    y = -0.0 - 43j
    assert x == y
    assert actually_equal(x, y, fuzzy=True)


def test_can_index_nan():
    nan = float('nan')
    assert real_index([nan, 0], nan) == 0
    assert real_index([nan, 0], float('nan')) == 0


def test_index_does_not_use_original_equal_on_inequal_types():
    snowman = '☃'
    x = [b'0\xff', 'hi', snowman, 'bar']
    assert real_index(x, snowman) == 2


def test_value_error_if_not_in_list():
    with pytest.raises(ValueError) as e:
        real_index([1, 2, 3], (1, 2))
    msg = e.value.args[0]
    assert '(1, 2)' in msg
    assert '[1, 2, 3]' in msg
