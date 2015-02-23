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
from hypothesis.descriptors import Just, OneOf, SampledFrom
from hypothesis.strategytable import StrategyTable
from hypothesis.searchstrategy import BadData
from hypothesis.internal.compat import text_type, binary_type


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
    (float, 252010555201342071294067021251680995120),
])
def test_simple_data_validation(descriptor, data):
    converter = StrategyTable.default().specification_for(descriptor)
    with pytest.raises(BadData):
        converter.from_basic(data)
