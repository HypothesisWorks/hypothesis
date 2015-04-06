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

import pytest
from hypothesis import given
from hypothesis.strategytests import strategy_test_suite
from hypothesis.searchstrategy import BasicStrategy
from hypothesis.searchstrategy.basic import basic_strategy
from hypothesis.internal.compat import hrange, integer_types
from hypothesis.internal.debug import timeout


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


@pytest.mark.parametrize('i', [0, 1, 2, 4, 8, 16, 32, 64, 127, 11, 10, 13])
def test_can_simplify_bitfields(i):
    bitfield = basic_strategy(
        parameter=lambda r: r.getrandbits(128),
        generate=lambda r, p: r.getrandbits(128) & p,
        simplify=simplify_bitfield,
        copy=lambda x: x,
    )

    assert minimal(bitfield, lambda x: x & (1 << i)) == 1 << i


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

    gc.collect()

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

    gc.collect()

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
