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
from collections import namedtuple

from hypothesis.specifiers import just, one_of, sampled_from, \
    floats_in_range, integers_in_range
from tests.common.specifiers import Descriptor, DescriptorWithValue
from hypothesis.strategytests import TemplatesFor, strategy_test_suitee
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.searchstrategy.narytree import NAryTree

TestIntegerRange = strategy_test_suitee(integers_in_range(0, 5))
TestFloatRange = strategy_test_suitee(floats_in_range(0.5, 10))
TestSampled = strategy_test_suitee(sampled_from(elements=(1, 2, 3)))

TestOneOf = strategy_test_suitee(one_of((int, int, bool)))
TestOneOfSameType = strategy_test_suitee(
    one_of((integers_in_range(1, 10), integers_in_range(8, 15)))
)
TestRandom = strategy_test_suitee(Random)
TestInts = strategy_test_suitee(int)
TestBoolLists = strategy_test_suitee([bool])
TestString = strategy_test_suitee(text_type)
BinaryString = strategy_test_suitee(binary_type)
TestIntBool = strategy_test_suitee((int, bool))
TestFloats = strategy_test_suitee(float)
TestComplex = strategy_test_suitee(complex)
TestJust = strategy_test_suitee(just('hi'))
TestTemplates = strategy_test_suitee(TemplatesFor({int}))

Stuff = namedtuple('Stuff', ('a', 'b'))
TestNamedTuple = strategy_test_suitee(Stuff(int, int))

TestTrees = strategy_test_suitee(NAryTree(int, int, int))

TestMixedSets = strategy_test_suitee({int, bool, float})
TestFrozenSets = strategy_test_suitee(frozenset({bool}))

TestNestedSets = strategy_test_suitee(frozenset({frozenset({complex})}))

TestMisc1 = strategy_test_suitee({(2, -374): frozenset({None})})
TestMisc2 = strategy_test_suitee({b'': frozenset({int})})
TestMisc3 = strategy_test_suitee(({type(None), str},),)

TestEmptyTuple = strategy_test_suitee(())
TestEmptyList = strategy_test_suitee([])
TestEmptySet = strategy_test_suitee(set())
TestEmptyFrozenSet = strategy_test_suitee(frozenset())
TestEmptyDict = strategy_test_suitee({})

TestDescriptor = strategy_test_suitee(Descriptor)
TestDescriptorWithValue = strategy_test_suitee(DescriptorWithValue)


def test_repr_has_specifier_in_it():
    suite = TestComplex(
        'test_can_round_trip_through_the_database')
    assert repr(suite) == 'strategy_test_suitee(complex)'
