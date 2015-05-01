# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

import sys
from decimal import Decimal
from fractions import Fraction
from random import Random
from collections import namedtuple

import pytest

import hypothesis.settings as hs
from hypothesis.internal.debug import timeout
from hypothesis import strategy
from hypothesis.specifiers import integers_from, floats_in_range, \
    integers_in_range, just, one_of, sampled_from, streaming
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.searchstrategy.narytree import NAryTree
from tests.common.basic import Bitfields
from hypothesis.utils.show import show


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


ABC = namedtuple('ABC', ('a', 'b', 'c'))

standard_types = [
    Bitfields,
    [], (), set(), frozenset(), {},
    NAryTree(bool, bool, bool),
    ABC(bool, bool, bool),
    ABC(bool, bool, int),
    {'a': int, 'b': bool},
    one_of((int, (bool,))),
    sampled_from(range(10)),
    one_of((just('a'), just('b'), just('c'))),
    sampled_from(('a', 'b', 'c')),
    int, integers_from(3), integers_in_range(-2 ** 32, 2 ** 64),
    float, floats_in_range(-2.0, 3.0),
    floats_in_range(3.14, 3.14),
    text_type, binary_type,
    bool,
    (bool, bool),
    frozenset({int}),
    complex,
    Fraction,
    Decimal,
    [[bool]],
    OrderedPair, ConstantList(int),
    strategy(streaming(int)).map(lambda x: list(x[:2]) and x),
    strategy(int).filter(lambda x: abs(x) > 100),
    floats_in_range(-sys.float_info.max, sys.float_info.max),
    None, Random,
]


def parametrize(args, values):
    return pytest.mark.parametrize(args, values, ids=list(map(show, values)))
