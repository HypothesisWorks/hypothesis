# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

import sys
import operator
from fractions import Fraction

import pytest
from flaky import flaky

from hypothesis import find, assume, settings
from tests.common import parametrize
from tests.common.debug import minimal
from hypothesis.strategies import just, sets, text, lists, tuples, \
    booleans, integers, fractions, frozensets, dictionaries, \
    sampled_from
from hypothesis.internal.compat import PY3, OrderedDict, hrange, reduce


def test_integers_from_minimizes_leftwards():
    assert minimal(integers(min_value=101)) == 101


def test_minimal_fractions_1():
    assert minimal(fractions()) == Fraction(0)


def test_minimal_fractions_2():
    assert minimal(fractions(), lambda x: x >= 1) == Fraction(1)


def test_minimal_fractions_3():
    assert minimal(
        lists(fractions()), lambda s: len(s) >= 20) == [Fraction(0)] * 20


def test_minimize_string_to_empty():
    assert minimal(text()) == u''


def test_minimize_one_of():
    for _ in hrange(100):
        assert minimal(integers() | text() | booleans()) in (
            0, u'', False
        )


def test_minimize_mixed_list():
    mixed = minimal(lists(integers() | text()), lambda x: len(x) >= 10)
    assert set(mixed).issubset(set((0, u'')))


def test_minimize_longer_string():
    assert minimal(text(), lambda x: len(x) >= 10) == u'0' * 10


def test_minimize_longer_list_of_strings():
    assert minimal(lists(text()), lambda x: len(x) >= 10) == [u''] * 10


def test_minimize_3_set():
    assert minimal(sets(integers()), lambda x: len(x) >= 3) in (
        set((0, 1, 2)),
        set((-1, 0, 1)),
    )


def test_minimize_3_set_of_tuples():
    assert minimal(
        sets(tuples(integers())),
        lambda x: len(x) >= 2) == set(((0,), (1,)))


def test_minimize_sets_of_sets():
    elements = integers(1, 100)
    size = 10
    set_of_sets = minimal(
        sets(frozensets(elements)), lambda s: len(s) >= size
    )
    assert frozenset() in set_of_sets
    assert len(set_of_sets) == size
    for s in set_of_sets:
        if len(s) > 1:
            assert any(
                s != t and t.issubset(s)
                for t in set_of_sets
            )


def test_can_simplify_flatmap_with_bounded_left_hand_size():
    assert minimal(
        booleans().flatmap(lambda x: lists(just(x))),
        lambda x: len(x) >= 10) == [False] * 10


def test_can_simplify_across_flatmap_of_just():
    assert minimal(integers().flatmap(just)) == 0


def test_can_simplify_on_right_hand_strategy_of_flatmap():
    assert minimal(integers().flatmap(lambda x: lists(just(x)))) == []


@flaky(min_passes=5, max_runs=5)
def test_can_ignore_left_hand_side_of_flatmap():
    assert minimal(
        integers().flatmap(lambda x: lists(integers())),
        lambda x: len(x) >= 10
    ) == [0] * 10


def test_can_simplify_on_both_sides_of_flatmap():
    assert minimal(
        integers().flatmap(lambda x: lists(just(x))),
        lambda x: len(x) >= 10
    ) == [0] * 10


def test_flatmap_rectangles():
    lengths = integers(min_value=0, max_value=10)

    def lists_of_length(n):
        return lists(sampled_from('ab'), min_size=n, max_size=n)

    xs = find(lengths.flatmap(
        lambda w: lists(lists_of_length(w))), lambda x: ['a', 'b'] in x,
        settings=settings(database=None, max_examples=2000)
    )
    assert xs == [['a', 'b']]


@flaky(min_passes=5, max_runs=5)
@parametrize(u'dict_class', [dict, OrderedDict])
def test_dictionary(dict_class):
    assert minimal(dictionaries(
        keys=integers(), values=text(),
        dict_class=dict_class)) == dict_class()

    x = minimal(
        dictionaries(keys=integers(), values=text(), dict_class=dict_class),
        lambda t: len(t) >= 3)
    assert isinstance(x, dict_class)
    assert set(x.values()) == set((u'',))
    for k in x:
        if k < 0:
            assert k + 1 in x
        if k > 0:
            assert k - 1 in x


def test_minimize_single_element_in_silly_large_int_range():
    ir = integers(-(2 ** 256), 2 ** 256)
    assert minimal(ir, lambda x: x >= -(2 ** 255)) == 0


def test_minimize_multiple_elements_in_silly_large_int_range():
    desired_result = [0] * 20

    ir = integers(-(2 ** 256), 2 ** 256)
    x = minimal(
        lists(ir),
        lambda x: len(x) >= 20,
        timeout_after=20,
    )
    assert x == desired_result


def test_minimize_multiple_elements_in_silly_large_int_range_min_is_not_dupe():
    ir = integers(0, 2 ** 256)
    target = list(range(20))

    x = minimal(
        lists(ir),
        lambda x: (
            assume(len(x) >= 20) and all(x[i] >= target[i] for i in target)),
        timeout_after=60,
    )
    assert x == target


@pytest.mark.skipif(PY3, reason=u'Python 3 has better integers')
def test_minimize_long():
    assert minimal(
        integers(), lambda x: type(x).__name__ == u'long') == sys.maxint + 1


def test_find_large_union_list():
    def large_mostly_non_overlapping(xs):
        assume(xs)
        assume(all(xs))
        union = reduce(operator.or_, xs)
        return len(union) >= 30

    result = minimal(
        lists(sets(integers())),
        large_mostly_non_overlapping, timeout_after=120)
    union = reduce(operator.or_, result)
    assert len(union) == 30
    assert max(union) == min(union) + len(union) - 1
    for x in result:
        for y in result:
            if x is not y:
                assert not (x & y)


@pytest.mark.parametrize('n', [0, 1, 10, 100, 1000])
def test_containment(n):
    iv = minimal(
        tuples(lists(integers()), integers()),
        lambda x: x[1] in x[0] and x[1] >= n,
        timeout_after=60
    )
    assert iv == ([n], n)


def test_duplicate_containment():
    ls, i = minimal(
        tuples(lists(integers()), integers()),
        lambda s: s[0].count(s[1]) > 1, timeout_after=100)
    assert ls == [0, 0]
    assert i == 0
