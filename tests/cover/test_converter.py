# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import pytest

from hypothesis.strategies import just, sets, text, lists, binary, \
    floats, one_of, tuples, randoms, booleans, integers, frozensets, \
    sampled_from, complex_numbers, fixed_dictionaries
from hypothesis.searchstrategy.narytree import n_ary_tree
from hypothesis.searchstrategy.strategies import BadData, strategy


@pytest.mark.parametrize((u'specifier', u'data'), [
    (sets(text()), 0j),
    (complex_numbers(), set(u'hi')),
    (lists(sets(booleans())), 0),
    (just(1), u'hi'),
    (binary(), 0.0),
    (binary(), frozenset()),
    (fixed_dictionaries({True: sets(integers())}), []),
    (randoms(), []),
    (integers(), u''),
    (integers(), [0, u'']),
    (text(), u'kittens'),
    (tuples(integers(), integers(), integers()), (1, 2)),
    (sampled_from((1, 2, 3)), u'fish'),
    (sampled_from((1, 2, 3)), 5),
    (sampled_from((1, 2, 3)), -2),
    (one_of(integers(), floats()), 1),
    (one_of(integers(), floats()), u'tv'),
    (one_of(integers(), floats()), [-2, 0]),
    (binary(), u'1'),
    (floats(), -1),
    (lists(one_of(frozensets(floats()), frozensets(floats()))), [[8, 0], []]),
    (floats(), 252010555201342071294067021251680995120),
    (tuples(integers(), integers()), 10),
    (n_ary_tree(integers(), integers(), integers()), []),
    (n_ary_tree(integers(), integers(), integers()), [1, 2, 3, 4, 5]),
    (floats(1, 2), (0, floats().to_basic(float(u'nan')))),
    (floats(1, 2), floats().to_basic(float(u'nan'))),
])
def test_simple_data_validation(specifier, data):
    converter = strategy(specifier)
    with pytest.raises(BadData):
        converter.from_basic(data)
