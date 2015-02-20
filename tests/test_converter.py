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

import pytest
import hypothesis.settings as hs
from hypothesis import Verifier, given, assume
from tests.common import small_table
from hypothesis.descriptors import Just, OneOf, SampledFrom
from tests.common.descriptors import DescriptorWithValue
from hypothesis.searchstrategy import RandomWithSeed
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.database.converter import BadData, WrongFormat, \
    ConverterTable, NotSerializeable


@pytest.mark.parametrize(('descriptor', 'value'), [
    ({int}, 0),
    (text_type, 0),
    (binary_type, RandomWithSeed(1)),
    (Just([]), 1),
    (Random, False),
    (complex, {1}),
    ((int, int), ('', '')),
    ((int, int), 'hi'),
    ((text_type, text_type), 'hi'),
    ((int, float, str, bytes, bool, complex), 0),
    (OneOf((int, float)), {0}),
    ({220: int, 437: int}, ''),
    ([binary_type], 0),
    (SampledFrom([1, 2, 3]), 0),
    ({'6': int}, {False: set()}),
    ((int, int), (1,)),
    (Just(value=set()), frozenset()),
    (SampledFrom((-30, 1)), True),
])
def test_simple_conversions(descriptor, value):
    converter = ConverterTable.default().specification_for(descriptor)
    with pytest.raises(WrongFormat):
        converter.to_basic(value)


@pytest.mark.parametrize(('descriptor', 'value'), [
    (float, 252010555201342071294067021251680995120),
])
def test_simple_back_conversions(descriptor, value):
    converter = ConverterTable.default().specification_for(descriptor)
    with pytest.raises(BadData):
        converter.from_basic(value)


@given(DescriptorWithValue, DescriptorWithValue, verifier=Verifier(
    strategy_table=small_table,
    settings=hs.Settings(max_examples=500),
))
def test_can_not_save_as_incompatible_examples(dav, dav2):
    strategy = small_table.strategy(dav.descriptor)
    assume(not strategy.could_have_produced(dav2.value))
    ft = ConverterTable.default()
    try:
        converter = ft.specification_for(dav.descriptor)
    except NotSerializeable:
        assume(False)

    with pytest.raises(WrongFormat):
        converter.to_basic(dav2.value)


@pytest.mark.parametrize(('descriptor', 'data'), [
    ({text_type}, 0j),
    (complex, {'hi'}),
    ([{bool}], 0),
    (Just(1), 'hi'),
    (binary_type, 0.0),
    (binary_type, frozenset()),
    ({True: {int}}, []),
    (Random, []),
    (int, ''),
    (text_type, []),
    ((int, int, int), (1, 2)),
    (SampledFrom((1, 2, 3)), 'fish'),
    (SampledFrom((1, 2, 3)), 5),
    (OneOf((int, float)), 1),
    (OneOf((int, float)), 'tv'),
    (binary_type, '1'),
    (float, -1),
    ([frozenset({float}), frozenset({float})], [[8, 0], []]),
])
def test_simple_data_validation(descriptor, data):
    converter = ConverterTable.default().specification_for(descriptor)
    with pytest.raises(BadData):
        converter.from_basic(data)


@given(DescriptorWithValue, DescriptorWithValue, verifier=Verifier(
    strategy_table=small_table,
    settings=hs.Settings(max_examples=1000),
))
def test_validates_data_from_database(dav, dav2):
    """
    This is a bit of a weird test. Basically we serialize data from one
    descriptor and parse it as another. This will sometimes produce a
    WrongFormat. That's fine. If it doesn't then there are two cases:

        1. These two types have a compatible representation. There's not much
           to do about that.
        2. A different exception is thrown. That's embarrassing and is only
           working by coincidence. That's bad too.

    This is mostly checking for consistency rather than correctness I'm afraid.
    It's hard to catch all the different behaviours you can get here.
    """
    converter = ConverterTable.default().specification_for(dav.descriptor)
    basic = converter.to_basic(dav.value)
    converter2 = ConverterTable().default().specification_for(dav2.descriptor)
    try:
        result = converter2.from_basic(basic)
    except BadData:
        return

    basic2 = converter2.to_basic(result)
    try:
        converter.from_basic(basic2)
    except BadData:
        pass
