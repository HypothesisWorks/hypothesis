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

import math
from random import Random
from collections import namedtuple

from hypothesis import Settings, strategy
from tests.common.basic import Bitfields, BoringBitfields, \
    simplify_bitfield
from hypothesis.stateful import StateMachineSearchStrategy
from hypothesis.strategies import just, none, sets, text, basic, lists, \
    binary, builds, floats, one_of, tuples, randoms, booleans, decimals, \
    integers, fractions, recursive, streaming, frozensets, dictionaries, \
    sampled_from, complex_numbers, fixed_dictionaries
from hypothesis.strategytests import mutate_basic, templates_for, \
    strategy_test_suite
from hypothesis.internal.compat import OrderedDict, hrange
from hypothesis.searchstrategy.morphers import MorpherStrategy
from hypothesis.searchstrategy.narytree import n_ary_tree

with Settings(average_list_length=5.0):
    TestIntegerRange = strategy_test_suite(integers(min_value=0, max_value=5))
    TestGiantIntegerRange = strategy_test_suite(
        integers(min_value=(-(2 ** 129)), max_value=(2 ** 129))
    )
    TestFloatRange = strategy_test_suite(floats(min_value=0.5, max_value=10))
    TestSampled10 = strategy_test_suite(sampled_from(elements=list(range(10))))
    TestSampled1 = strategy_test_suite(sampled_from(elements=(1,)))
    TestSampled2 = strategy_test_suite(sampled_from(elements=(1, 2)))

    TestIntegersFrom = strategy_test_suite(integers(min_value=13))
    TestIntegersFrom = strategy_test_suite(integers(min_value=1 << 1024))

    TestOneOf = strategy_test_suite(one_of(
        integers(), integers(), booleans()))

    TestOneOfSameType = strategy_test_suite(
        one_of(
            integers(min_value=1, max_value=10),
            integers(min_value=8, max_value=15),
        )
    )
    TestRandom = strategy_test_suite(randoms())
    TestInts = strategy_test_suite(integers())
    TestBoolLists = strategy_test_suite(lists(booleans()))
    TestDictionaries = strategy_test_suite(
        dictionaries(keys=tuples(integers(), integers()), values=booleans()))
    TestOrderedDictionaries = strategy_test_suite(
        dictionaries(
            keys=integers(), values=integers(), dict_class=OrderedDict))
    TestString = strategy_test_suite(text())
    BinaryString = strategy_test_suite(binary())
    TestIntBool = strategy_test_suite(tuples(integers(), booleans()))
    TestFloats = strategy_test_suite(floats())
    TestComplex = strategy_test_suite(complex_numbers())
    TestJust = strategy_test_suite(just(u'hi'))
    TestTemplates = strategy_test_suite(templates_for(sets(integers())))

    TestEmptyString = strategy_test_suite(text(alphabet=u''))
    TestSingleString = strategy_test_suite(strategy(
        text(alphabet=u'a'), Settings(average_list_length=10.0)))
    TestManyString = strategy_test_suite(text(alphabet=u'abcdef☃'))

    Stuff = namedtuple(u'Stuff', (u'a', u'b'))
    TestNamedTuple = strategy_test_suite(
        builds(Stuff, integers(), integers()))

    TestTrees = strategy_test_suite(
        n_ary_tree(integers(), integers(), integers()))

    TestMixedSets = strategy_test_suite(sets(
        one_of(integers(), booleans(), floats())))
    TestFrozenSets = strategy_test_suite(frozensets(booleans()))

    TestNestedSets = strategy_test_suite(
        frozensets(frozensets(integers(), max_size=2)))

    TestMisc1 = strategy_test_suite(fixed_dictionaries(
        {(2, -374): frozensets(none())}))
    TestMisc2 = strategy_test_suite(fixed_dictionaries(
        {b'': frozensets(integers())}))
    TestMisc3 = strategy_test_suite(tuples(sets(none() | text())))

    TestEmptyTuple = strategy_test_suite(tuples())
    TestEmptyList = strategy_test_suite(lists(max_size=0))
    TestEmptySet = strategy_test_suite(sets(max_size=0))
    TestEmptyFrozenSet = strategy_test_suite(frozensets(max_size=0))
    TestEmptyDict = strategy_test_suite(fixed_dictionaries({}))

    TestDecimal = strategy_test_suite(decimals())
    TestFraction = strategy_test_suite(fractions())

    TestNonEmptyLists = strategy_test_suite(
        lists(integers()).filter(bool)
    )

    TestNoneLists = strategy_test_suite(lists(none()))

    TestConstantLists = strategy_test_suite(
        integers().flatmap(lambda i: lists(just(i)))
    )

    TestListsWithUniqueness = strategy_test_suite(
        lists(lists(integers()), unique_by=lambda x: tuple(sorted(x))))

    TestOrderedPairs = strategy_test_suite(
        strategy(integers(min_value=1, max_value=200)).flatmap(
            lambda e: tuples(integers(min_value=0, max_value=e - 1), just(e))
        )
    )

    TestMappedSampling = strategy_test_suite(
        lists(integers(), min_size=1).flatmap(sampled_from)
    )

    TestDiverseFlatmap = strategy_test_suite(
        sampled_from((
            lists(integers()), lists(text()), tuples(text(), text()),
            booleans(), lists(complex_numbers())
        )).flatmap(lambda x: x)
    )

    def integers_from(x):
        return integers(min_value=x)

    TestManyFlatmaps = strategy_test_suite(
        integers()
        .flatmap(integers_from)
        .flatmap(integers_from)
        .flatmap(integers_from)
        .flatmap(integers_from)
    )

    TestBareMorphers = strategy_test_suite(MorpherStrategy())
    TestMasqueradingMorphers = strategy_test_suite(
        MorpherStrategy().map(lambda m: m.become(lists(integers()))))

    TestIntStreams = strategy_test_suite(streaming(integers()))
    TestStreamLists = strategy_test_suite(streaming(integers()))
    TestIntStreamStreams = strategy_test_suite(
        streaming(streaming(integers())))

    TestBoringBitfieldsClass = strategy_test_suite(basic(BoringBitfields))
    TestBitfieldsClass = strategy_test_suite(basic(Bitfields))
    TestBitfieldsInstance = strategy_test_suite(basic(Bitfields()))

    TestBitfields = strategy_test_suite(lists(
        basic(
            generate=lambda r, p: r.getrandbits(128),
            simplify=simplify_bitfield,
            copy=lambda x: x,
        )
    ))

    TestBitfieldsSet = strategy_test_suite(sets(
        basic(
            generate=lambda r, p: r.getrandbits(128),
            simplify=simplify_bitfield,
            copy=lambda x: x,
        )
    ))

    TestBitfield = strategy_test_suite(
        basic(
            generate=lambda r, p: r.getrandbits(128),
            simplify=simplify_bitfield,
            copy=lambda x: x,
        )
    )

    TestBitfieldJustGenerate = strategy_test_suite(
        basic(
            generate=lambda r, p: r.getrandbits(128),
        )
    )

    TestBitfieldWithParameter = strategy_test_suite(
        basic(
            generate_parameter=lambda r: r.getrandbits(128),
            generate=lambda r, p: r.getrandbits(128) & p,
        )
    )

    TestRecursiveLowLeaves = strategy_test_suite(
        recursive(
            booleans(),
            lambda x: tuples(x, x),
            max_leaves=3,
        )
    )

    TestRecursiveHighLeaves = strategy_test_suite(
        recursive(
            booleans(),
            lambda x: lists(x, min_size=2, max_size=10),
            max_leaves=200,
        )
    )

    TestJSON = strategy_test_suite(
        recursive(
            floats().filter(lambda f: not math.isnan(f) or math.isinf(f)) |
            text() | booleans() | none(),
            lambda js:
                lists(js, average_size=2) |
                dictionaries(text(), js, average_size=2),
            max_leaves=10))

    TestWayTooClever = strategy_test_suite(
        recursive(
            frozensets(integers(), min_size=1),
            lambda x: frozensets(x, min_size=2, max_size=4)).flatmap(
            sampled_from
        )
    )


TestStatemachine = strategy_test_suite(StateMachineSearchStrategy())


def test_repr_has_specifier_in_it():
    suite = TestComplex(
        u'test_can_round_trip_through_the_database')
    assert repr(suite) == u'strategy_test_suite(%r)' % (complex_numbers(),)


def test_can_mutate_non_basic():
    mutate_basic(1.0, Random(0))


def test_can_mutate_large_int():
    r = Random(0)
    for _ in hrange(20):
        mutate_basic(1 << 1024, r)
