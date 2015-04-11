# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import gc
import sys

import pytest
from hypothesis import given
from hypothesis.strategytests import strategy_test_suite
from hypothesis.internal.debug import timeout
from hypothesis.searchstrategy import BasicStrategy
from hypothesis.internal.compat import hrange, integer_types
from hypothesis.searchstrategy.basic import basic_strategy

from .test_example_quality import minimal


def simplify_bitfield(random, value):
    for i in hrange(128):
        k = 1 << i
        if value & k:
            yield value & (~k)


class BoringBitfields(BasicStrategy):

    def generate(self, random, parameter_value):
        return random.getrandbits(128)


class Bitfields(BasicStrategy):

    def generate_parameter(self, random):
        return random.getrandbits(128)

    def generate(self, random, parameter_value):
        return parameter_value & random.getrandbits(128)

    def simplify(self, random, value):
        return simplify_bitfield(random, value)

    def copy(self, value):
        return value


def popcount(x):
    # don't judge
    tot = 0
    while x:
        tot += (x & 1)
        x >>= 1
    return tot


TestBoringBitfieldsClass = strategy_test_suite(BoringBitfields)
TestBitfieldsClass = strategy_test_suite(Bitfields)
TestBitfieldsInstance = strategy_test_suite(Bitfields())


TestBitfields = strategy_test_suite([
    basic_strategy(
        generate=lambda r, p: r.getrandbits(128),
        simplify=simplify_bitfield,
        copy=lambda x: x,
    )
])

TestBitfieldsSet = strategy_test_suite({
    basic_strategy(
        generate=lambda r, p: r.getrandbits(128),
        simplify=simplify_bitfield,
        copy=lambda x: x,
    )
})


TestBitfield = strategy_test_suite(
    basic_strategy(
        generate=lambda r, p: r.getrandbits(128),
        simplify=simplify_bitfield,
        copy=lambda x: x,
    )
)

TestBitfieldJustGenerate = strategy_test_suite(
    basic_strategy(
        generate=lambda r, p: r.getrandbits(128),
    )
)


TestBitfieldWithParameter = strategy_test_suite(
    basic_strategy(
        parameter=lambda r: r.getrandbits(128),
        generate=lambda r, p: r.getrandbits(128) & p,
    )
)


@pytest.mark.parametrize('i', range(128))
def test_can_simplify_bitfields(i):
    bitfield = basic_strategy(
        parameter=lambda r: r.getrandbits(128),
        generate=lambda r, p: r.getrandbits(128) & p,
        simplify=simplify_bitfield,
        copy=lambda x: x,
    )

    assert minimal(bitfield, lambda x: x & (1 << i)) == 1 << i


def gc_clear():
    try:
        sys.exc_clear()
    except AttributeError:
        pass
    gc.collect()


def test_cache_is_cleaned_up_on_gc_1():
    st = basic_strategy(
        generate=lambda r, p: r.getrandbits(128),
        simplify=simplify_bitfield,
        copy=lambda x: x,
    )

    @given(st)
    def test_all_good(x):
        pass

    test_all_good()

    gc_clear()

    assert len(st.reify_cache) == 0


def test_cache_is_cleaned_up_on_gc_2():
    st = basic_strategy(
        generate=lambda r, p: r.getrandbits(128),
        simplify=simplify_bitfield,
        copy=lambda x: x,
    )

    @given(st)
    def test_all_bad(x):
        assert False

    try:
        test_all_bad()
    except AssertionError:
        pass

    gc_clear()

    assert all(isinstance(v, integer_types) for v in st.reify_cache.values())
    assert len(st.reify_cache) == 0, len(st.reify_cache)


def test_does_not_get_stuck_in_a_loop():
    bad_strategy = basic_strategy(
        generate=lambda r, p: 1,
        simplify=lambda r, v: [v]
    )

    @timeout(2)
    @given(bad_strategy)
    def oh_noes(x):
        assert x != 1
    with pytest.raises(AssertionError):
        oh_noes()


@pytest.mark.parametrize('c', range(30))
def test_can_simplify_bitfields_with_composite(c):
    bitfield = basic_strategy(
        parameter=lambda r: r.getrandbits(128),
        generate=lambda r, p: r.getrandbits(128) & p,
        simplify=simplify_bitfield,
        copy=lambda x: x,
    )

    t = minimal(bitfield, lambda x: popcount(x) >= c)
    assert popcount(t) == c


def has_adjacent_one_bits(x):
    while x:
        if x & 3 == 3:
            return True
        x >>= 1
    return x


def test_can_find_adjacent_one_bits():
    class Nope(Exception):
        pass

    @given(Bitfields)
    def has_no_adjacent_one_bits(x):
        if has_adjacent_one_bits(x):
            raise Nope()

    for _ in range(5):
        with pytest.raises(Nope):
            has_no_adjacent_one_bits()
