# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import gc
import sys
from random import Random

import pytest
from hypothesis import given
from tests.common.basic import Bitfields, BoringBitfields, \
    simplify_bitfield
from tests.common.utils import fails
from hypothesis.strategies import basic
from hypothesis.internal.debug import minimal, timeout, some_template
from hypothesis.internal.compat import integer_types
from hypothesis.searchstrategy.basic import basic_strategy


def popcount(x):
    # don't judge
    tot = 0
    while x:
        tot += (x & 1)
        x >>= 1
    return tot


@pytest.mark.parametrize(u'i', [0, 1, 3, 10, 21, 65, 127])
def test_can_simplify_bitfields(i):
    bitfield = basic_strategy(
        parameter=lambda r: r.getrandbits(128),
        generate=lambda r, p: r.getrandbits(128) & p,
        simplify=simplify_bitfield,
        copy=lambda x: x,
    )

    assert minimal(bitfield, lambda x: x & (1 << i)) == 1 << i


def test_can_find_bitfields_without_simplifying():
    assert minimal(
        basic_strategy(generate=lambda r, p: r.getrandbits(128)),
        lambda x: x & 1
    )


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


@fails
@given(basic(BoringBitfields))
def test_boring_failure(x):
    assert x & 1


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


@pytest.mark.parametrize(u'c', range(30))
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

    @given(basic(Bitfields))
    def has_no_adjacent_one_bits(x):
        if has_adjacent_one_bits(x):
            raise Nope()

    for _ in range(5):
        with pytest.raises(Nope):
            has_no_adjacent_one_bits()


def test_can_provide_just_param_and_generate():
    bf = basic(
        generate_parameter=lambda r: r.getrandbits(128),
        generate=lambda r, p: r.getrandbits(128) & p,
    )
    assert minimal(bf)


def test_simplifying_results_in_strictly_simpler():
    random = Random(u'test_simplifying_results_in_strictly_simpler')
    strat = basic(Bitfields)
    template = some_template(strat, random)
    for shrunk_template in strat.full_simplify(random, template):
        assert strat.strictly_simpler(shrunk_template, template)


def test_can_recalculate_shrinks_without_reify_cache():
    random = Random(u'test_can_recalculate_shrinks_without_reify_cache')
    strat = basic(Bitfields)
    template = some_template(strat, random)
    for shrunk_template in strat.full_simplify(random, template):
        strat.wrapped_strategy.reify_cache.pop(shrunk_template, None)
        strat.wrapped_strategy.reify_cache.pop(template, None)
        assert not (~strat.reify(template) & strat.reify(shrunk_template))
    new_template = strat.from_basic(strat.to_basic(template))
    assert strat.reify(template) == strat.reify(new_template)
