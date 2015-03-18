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

from hypothesis.descriptors import just, one_of, sampled_from, \
    floats_in_range, integers_in_range
from tests.common.descriptors import Descriptor, DescriptorWithValue
from hypothesis.descriptortests import TemplatesFor, descriptor_test_suite
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.searchstrategy.narytree import NAryTree

TestIntegerRange = descriptor_test_suite(integers_in_range(0, 5))
TestFloatRange = descriptor_test_suite(floats_in_range(0.5, 10))
TestSampled = descriptor_test_suite(sampled_from(elements=(1, 2, 3)))

TestOneOf = descriptor_test_suite(one_of((int, int, bool)))
TestOneOfSameType = descriptor_test_suite(
    one_of((integers_in_range(1, 10), integers_in_range(8, 15)))
)
TestRandom = descriptor_test_suite(Random)
TestInts = descriptor_test_suite(int)
TestBoolLists = descriptor_test_suite([bool])
TestString = descriptor_test_suite(text_type)
BinaryString = descriptor_test_suite(binary_type)
TestIntBool = descriptor_test_suite((int, bool))
TestFloats = descriptor_test_suite(float)
TestComplex = descriptor_test_suite(complex)
TestJust = descriptor_test_suite(just('hi'))
TestTemplates = descriptor_test_suite(TemplatesFor({int}))

Stuff = namedtuple('Stuff', ('a', 'b'))
TestNamedTuple = descriptor_test_suite(Stuff(int, int))

TestTrees = descriptor_test_suite(NAryTree(int, int, int))

TestMixedSets = descriptor_test_suite({int, bool, float})
TestFrozenSets = descriptor_test_suite(frozenset({bool}))

TestNestedSets = descriptor_test_suite(frozenset({frozenset({complex})}))

TestMisc1 = descriptor_test_suite({(2, -374): frozenset({None})})
TestMisc2 = descriptor_test_suite({b'': frozenset({int})})
TestMisc3 = descriptor_test_suite(({type(None), str},),)

TestEmptyTuple = descriptor_test_suite(())
TestEmptyList = descriptor_test_suite([])
TestEmptySet = descriptor_test_suite(set())
TestEmptyFrozenSet = descriptor_test_suite(frozenset())
TestEmptyDict = descriptor_test_suite({})

TestDescriptor = descriptor_test_suite(Descriptor)
TestDescriptorWithValue = descriptor_test_suite(DescriptorWithValue)


def test_repr_has_descriptor_in_it():
    suite = TestComplex(
        'test_can_round_trip_through_the_database')
    assert repr(suite) == 'descriptor_test_suite(complex)'
