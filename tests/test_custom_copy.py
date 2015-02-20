# coding=utf-8

# reifyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a reify of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
from hypothesis.params import CompositeParameter
from hypothesis.descriptors import one_of
from hypothesis.strategytable import StrategyTable
from hypothesis.searchstrategy import SearchStrategy


class HasAnId(object):

    def __init__(self, i):
        self.i = i

    def __repr__(self):
        return 'HasAnId(%r)' % (self.i,)

    def __eq__(self, other):
        return (type(other) == HasAnId) and (self.i == other.i)


class HasAnIdStrategy(SearchStrategy):
    parameter = CompositeParameter()
    descriptor = HasAnId

    def produce(self, random, pv):
        return HasAnId(0)

    def custom_reify(self, value):
        return HasAnId(value.i + 1)


StrategyTable.default().define_specification_for(
    HasAnId, lambda s, d: HasAnIdStrategy()
)


def test_basic_does_not_have_custom_reify():
    assert not StrategyTable().strategy(int).has_custom_reify()
    assert not StrategyTable().strategy([int]).has_custom_reify()
    assert not StrategyTable().strategy({int}).has_custom_reify()
    assert not StrategyTable().strategy([int, bool]).has_custom_reify()
    assert not StrategyTable().strategy((int, int)).has_custom_reify()


def test_has_custom_reify():
    assert StrategyTable().strategy(HasAnId).has_custom_reify()


def test_tuple_has_custom_reify():
    assert StrategyTable().strategy((HasAnId,)).has_custom_reify()


def test_list_has_custom_reify():
    assert StrategyTable().strategy([HasAnId]).has_custom_reify()


def test_mixed_list_has_custom_reify():
    assert StrategyTable().strategy([HasAnId, int]).has_custom_reify()


def test_set_has_custom_reify():
    assert StrategyTable().strategy({HasAnId}).has_custom_reify()


def test_dict_has_custom_reify():
    assert StrategyTable().strategy({1: HasAnId, 2: int}).has_custom_reify()


def test_uses_custom_reify():
    assert StrategyTable().strategy(HasAnId).reify(HasAnId(0)) == HasAnId(1)
    assert StrategyTable().strategy((HasAnId,)).reify(
        (HasAnId(0),)) == (HasAnId(1),)
    assert StrategyTable().strategy([HasAnId]).reify(
        [HasAnId(0)]) == [HasAnId(1)]
    assert StrategyTable().strategy([int, HasAnId]).reify(
        [HasAnId(0)]) == [HasAnId(1)]
    assert StrategyTable().strategy({1: HasAnId}).reify(
        {1: HasAnId(0)}) == {1: HasAnId(1)}


def test_custom_reify_one_of_errors_on_bad_value():
    with pytest.raises(ValueError):
        StrategyTable().strategy(one_of((int, bool, HasAnId))).reify('foo')


def test_custom_reify_raises_error_if_not_supported():
    with pytest.raises(NotImplementedError):
        StrategyTable().strategy(int).custom_reify(1)
