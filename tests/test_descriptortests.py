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

from hypothesis.descriptors import one_of, integers_in_range
from hypothesis.descriptortests import descriptor_test_suite
from hypothesis.internal.compat import text_type, binary_type

TestOneOf = descriptor_test_suite(one_of((int, bool)))
TestOneOfSameType = descriptor_test_suite(
    one_of((integers_in_range(1, 10), integers_in_range(8, 15)))
)
TestRandom = descriptor_test_suite(Random)
TestInts = descriptor_test_suite(int)
TestBoolLists = descriptor_test_suite(
    [bool], simplify_is_unique=False
)
TestString = descriptor_test_suite(
    text_type, simplify_is_unique=False
)
BinaryString = descriptor_test_suite(
    binary_type, simplify_is_unique=False
)
TestIntBool = descriptor_test_suite((int, bool))
TestFloat = descriptor_test_suite(float)
TestComplex = descriptor_test_suite(complex)
TestComplex = descriptor_test_suite((float, float))
