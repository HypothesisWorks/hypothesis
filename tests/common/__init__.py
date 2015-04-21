# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

import hypothesis.settings as hs
from hypothesis.internal.debug import timeout
from hypothesis import strategy

from decimal import Decimal
from fractions import Fraction

from hypothesis.specifiers import integers_from, floats_in_range, \
    integers_in_range, just, one_of, sampled_from
from hypothesis.internal.compat import text_type, binary_type
from collections import namedtuple

settings = hs.Settings(max_examples=100, timeout=4)

__all__ = ['small_verifier', 'timeout', 'standard_types', 'OrderedPair']


OrderedPair = namedtuple('OrderedPair', ('left', 'right'))


@strategy.extend_static(OrderedPair)
def ordered_pair_strategy(_, settings):
    return strategy(int, settings).flatmap(
        lambda right: strategy(integers_from(0), settings).map(
            lambda length: OrderedPair(right - length, right)))


ConstantList = namedtuple('ConstantList', ('spec',))


@strategy.extend(ConstantList)
def constant_list_strategy(spec, settings):
    return strategy(spec.spec, settings).flatmap(
        lambda v: [just(v)],
    )


standard_types = [
    one_of((int, (bool,))),
    sampled_from(range(10)),
    one_of((just('a'), just('b'), just('c'))),
    sampled_from(('a', 'b', 'c')),
    int, integers_from(3), integers_in_range(-2 ** 32, 2 ** 64),
    float, floats_in_range(-2.0, 3.0),
    text_type, binary_type,
    bool,
    (bool, bool),
    frozenset({int}),
    complex,
    Fraction,
    Decimal,
    [[bool]],
    OrderedPair, ConstantList(int),
]
