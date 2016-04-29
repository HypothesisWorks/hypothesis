# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import math
from collections import namedtuple

from hypothesis.strategies import just, none, sets, text, lists, binary, \
    builds, floats, one_of, tuples, randoms, booleans, decimals, \
    integers, composite, fractions, recursive, streaming, frozensets, \
    dictionaries, sampled_from, complex_numbers, fixed_dictionaries
from hypothesis.strategytests import strategy_test_suite
from hypothesis.internal.compat import OrderedDict

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
TestBoolLists = strategy_test_suite(lists(booleans(), average_size=5.0))
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

TestEmptyString = strategy_test_suite(text(alphabet=u''))
TestSingleString = strategy_test_suite(
    text(alphabet=u'a', average_size=10.0))
TestManyString = strategy_test_suite(text(alphabet=u'abcdef☃'))

Stuff = namedtuple(u'Stuff', (u'a', u'b'))
TestNamedTuple = strategy_test_suite(
    builds(Stuff, integers(), integers()))

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
    lists(integers(), average_size=5.0).filter(bool)
)

TestNoneLists = strategy_test_suite(lists(none(), average_size=5.0))

TestConstantLists = strategy_test_suite(
    integers().flatmap(lambda i: lists(just(i), average_size=5.0))
)

TestListsWithUniqueness = strategy_test_suite(
    lists(
        lists(integers(), average_size=5.0),
        average_size=5.0,
        unique_by=lambda x: tuple(sorted(x)))
)

TestOrderedPairs = strategy_test_suite(
    integers(min_value=1, max_value=200).flatmap(
        lambda e: tuples(integers(min_value=0, max_value=e - 1), just(e))
    )
)

TestMappedSampling = strategy_test_suite(
    lists(integers(), min_size=1, average_size=5.0).flatmap(sampled_from)
)

TestDiverseFlatmap = strategy_test_suite(
    sampled_from((
        lists(integers(), average_size=5.0),
        lists(text(), average_size=5.0), tuples(text(), text()),
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

TestIntStreams = strategy_test_suite(streaming(integers()))
TestStreamLists = strategy_test_suite(streaming(integers()))
TestIntStreamStreams = strategy_test_suite(
    streaming(streaming(integers())))

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
        frozensets(integers(), min_size=1, average_size=2.0),
        lambda x: frozensets(x, min_size=2, max_size=4)).flatmap(
        sampled_from
    )
)


@composite
def tight_integer_list(draw):
    x = draw(integers())
    y = draw(integers(min_value=x))
    return draw(lists(integers(min_value=x, max_value=y)))

TestComposite = strategy_test_suite(tight_integer_list())


def test_repr_has_specifier_in_it():
    suite = TestComplex(
        u'test_will_find_a_constant_failure')
    assert repr(suite) == u'strategy_test_suite(%r)' % (complex_numbers(),)
