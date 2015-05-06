# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import sys
import math
import operator
from decimal import Decimal
from fractions import Fraction
from collections import Counter, OrderedDict

import pytest
from hypothesis import Settings, assume, strategy
from tests.common import OrderedPair, parametrize, constant_list
from hypothesis.specifiers import just, one_of, dictionary, \
    integers_from, integers_in_range
from hypothesis.internal.debug import minimal
from hypothesis.internal.compat import PY3, hrange, reduce, text_type, \
    binary_type


def test_minimize_list_on_large_structure():
    def test_list_in_range(xs):
        assume(len(xs) >= 30)
        return len([
            x for x in xs
            if x >= 10
        ]) >= 60

    assert minimal([int], test_list_in_range) == [10] * 60


def test_minimize_list_of_sets_on_large_structure():
    def test_list_in_range(xs):
        assume(len(xs) >= 50)
        return len(list(filter(None, xs))) >= 50

    x = minimal(
        [frozenset({int})], test_list_in_range,
        timeout_after=20,
    )
    assert len(x) == 50
    assert len(set(x)) == 1


def test_integers_from_minizes_leftwards():
    assert minimal(integers_from(101)) == 101


def test_minimal_fractions_1():
    assert minimal(Fraction) == Fraction(0)


def test_minimal_fractions_2():
    assert minimal(Fraction, lambda x: x >= 1) == Fraction(1)


def test_minimal_fractions_3():
    assert minimal([Fraction], lambda s: len(s) >= 20) == [Fraction(0)] * 20


def test_minimal_fractions_4():
    assert minimal(
        [Fraction], lambda s: len(s) >= 20 and all(t >= 1 for t in s)
    ) == [Fraction(1)] * 20


def test_finding_decimals_with_defined_precision():
    def is_integral(x):
        try:
            return x == int(x)
        except (ValueError, OverflowError):
            return False

    assert minimal(Decimal, is_integral) == Decimal(0)
    minimal(Decimal, lambda x: is_integral(x * 100) and 0 < x < 1)


def test_minimize_list_of_floats_on_large_structure():
    def test_list_in_range(xs):
        assume(len(xs) >= 50)
        return len([
            x for x in xs
            if x >= 3
        ]) >= 30

    result = minimal([float], test_list_in_range)
    result.sort()
    assert result == [0.0] * 20 + [3.0] * 30


def test_minimize_string_to_empty():
    assert minimal(text_type) == ''


def test_minimize_one_of():
    for _ in hrange(100):
        assert minimal(one_of((int, str, bool))) in (
            0, '', False
        )


def test_minimize_mixed_list():
    mixed = minimal([int, text_type], lambda x: len(x) >= 10)
    assert set(mixed).issubset({0, ''})


def test_minimize_longer_string():
    assert minimal(text_type, lambda x: len(x) >= 10) == '0' * 10


def test_minimize_longer_list_of_strings():
    assert minimal([text_type], lambda x: len(x) >= 10) == [''] * 10


def test_minimize_3_set():
    assert minimal({int}, lambda x: len(x) >= 3) in (
        {0, 1, 2},
        {-1, 0, 1},
    )


def test_minimize_3_set_of_tuples():
    assert minimal({(int,)}, lambda x: len(x) >= 2) == {(0,), (1,)}


def test_minimize_sets_of_sets():
    elements = integers_in_range(1, 100)
    size = 15
    set_of_sets = minimal(
        {frozenset({elements})}, lambda s: len(s) >= size
    )
    assert frozenset() in set_of_sets
    assert len(set_of_sets) == size
    for s in set_of_sets:
        if len(s) > 1:
            assert any(
                s != t and t.issubset(s)
                for t in set_of_sets
            )


@pytest.mark.parametrize(
    ('string',), [(text_type,), (binary_type,)],
    ids=['text_type', 'binary_type']
)
def test_minimal_unsorted_strings(string):
    def dedupe(xs):
        result = []
        for x in xs:
            if x not in result:
                result.append(x)
        return result

    result = minimal(
        strategy([string]).map(dedupe),
        lambda xs: assume(len(xs) >= 5) and sorted(xs) != xs
    )
    assert len(result) == 5
    for example in result:
        if len(example) > 1:
            for i in hrange(len(example)):
                assert example[:i] in result


def test_finds_list_with_plenty_duplicates():
    def is_good(xs):
        xs = list(filter(None, xs))
        assume(xs)
        return max(Counter(xs).values()) >= 3

    result = minimal(
        [str], is_good
    )
    assert len(result) == 3
    assert len(set(result)) == 1
    assert len(result[0]) == 1


def test_minimal_mixed_list_propagates_leftwards():
    # one_of simplification can't actually simplify to the left, but it regards
    # instances of the leftmost type as strictly simpler. This means that if we
    # have any bools in the list we can clone them to replace the more complex
    # examples to the right.
    # The check that we have at least one bool is required for this to work,
    # otherwise the features that ensure sometimes we can get a list of all of
    # one type will occasionally give us an example which doesn't contain any
    # bools to clone
    def long_list_with_enough_bools(x):
        if len(x) < 50:
            return False
        if len([t for t in x if isinstance(t, bool)]) < 10:
            return False
        return True

    assert minimal([bool, (int,)], long_list_with_enough_bools) == [False] * 50


def test_tuples_do_not_block_cloning():
    assert minimal(
        [(one_of((bool, (int,))),)],
        lambda x: len(x) >= 50 and any(isinstance(t[0], bool) for t in x)
    ) == [(False,)] * 50


def test_can_simplify_flatmap_with_bounded_left_hand_size():
    assert minimal(
        strategy(bool).flatmap(lambda x: [just(x)]),
        lambda x: len(x) >= 10) == [False] * 10


def test_can_simplify_across_flatmap_of_just():
    assert minimal(strategy(int).flatmap(just)) == 0


def test_can_simplify_on_right_hand_strategy_of_flatmap():
    assert minimal(strategy(int).flatmap(lambda x: [just(x)])) == []


def test_can_ignore_left_hand_side_of_flatmap():
    assert minimal(
        strategy(int).flatmap(lambda x: [int]),
        lambda x: len(x) >= 10
    ) == [0] * 10


def test_can_simplify_on_both_sides_of_flatmap():
    assert minimal(
        strategy(int).flatmap(lambda x: [just(x)]),
        lambda x: len(x) >= 10
    ) == [0] * 10


@parametrize('dict_class', [dict, OrderedDict])
def test_dictionary(dict_class):
    assert minimal(dictionary(int, text_type, dict_class)) == dict_class()

    x = minimal(dictionary(int, text_type, dict_class), lambda t: len(t) >= 3)
    assert isinstance(x, dict_class)
    assert set(x.values()) == {''}
    for k in x:
        if k < 0:
            assert k + 1 in x
        if k > 0:
            assert k - 1 in x


def test_minimize_single_element_in_silly_large_int_range():
    ir = integers_in_range(-(2 ** 256), 2 ** 256)
    assert minimal(ir, lambda x: x >= -(2 ** 255)) == -(2 ** 255)


def test_minimize_multiple_elements_in_silly_large_int_range():
    desired_result = [-(2 ** 255)] * 20

    def condition(x):
        assume(len(x) >= 20)
        return all(t >= -(2 ** 255) for t in x)

    ir = integers_in_range(-(2 ** 256), 2 ** 256)
    x = minimal(
        [ir],
        condition,
        # This is quite hard and I don't yet have a good solution for
        # making it less so, so this one gets a higher timeout.
        timeout_after=20,
    )
    assert x == desired_result


def test_minimize_multiple_elements_in_silly_large_int_range_min_is_not_dupe():
    ir = integers_in_range(0, 2 ** 256)
    target = list(range(20))

    x = minimal(
        [ir],
        lambda x: (
            assume(len(x) >= 20) and all(x[i] >= target[i] for i in target))
    )
    assert x == target


def test_minimize_one_of_distinct_types():
    x = minimal(
        (one_of((bool, binary_type)), one_of((bool, binary_type))),
        lambda x: type(x[0]) != type(x[1])
    )
    assert x in (
        (False, b''),
        (b'', False)
    )


@pytest.mark.skipif(PY3, reason='Python 3 has better integers')
def test_minimize_long():
    assert minimal(int, lambda x: type(x).__name__ == 'long') == sys.maxint + 1


def test_non_reversible_ints_as_decimals():
    def not_reversible(xs):
        ts = list(map(Decimal, xs))
        return sum(ts) != sum(reversed(ts))

    sigh = minimal([int], not_reversible, timeout_after=30)
    assert len(sigh) <= 10


def test_non_reversible_fractions_as_decimals():
    def not_reversible(xs):
        xs = [Decimal(x.numerator) / x.denominator for x in xs]
        return sum(xs) != sum(reversed(xs))

    sigh = minimal([Fraction], not_reversible, timeout_after=20)
    assert len(sigh) < 10


def test_non_reversible_decimals():
    def not_reversible(xs):
        assume(all(x.is_finite() for x in xs))
        return sum(xs) != sum(reversed(xs))
    sigh = minimal([Decimal], not_reversible, timeout_after=30)
    assert len(sigh) < 10


def length_of_longest_ordered_sequence(xs):
    if not xs:
        return 0
    # FIXME: Needlessly O(n^2) algorithm, but it's a test so eh.
    lengths = [-1] * len(xs)
    lengths[-1] = 1
    for i in hrange(len(xs) - 2, -1, -1):
        assert lengths[i] == -1
        for j in hrange(i + 1, len(xs)):
            assert lengths[j] >= 1
            if xs[j] > xs[i]:
                lengths[i] = max(lengths[i], lengths[j] + 1)
        if lengths[i] < 0:
            lengths[i] = 1
    assert all(t >= 1 for t in lengths)
    return max(lengths)


def test_increasing_sequence():
    k = 6
    xs = minimal(
        [int], lambda t: (
            len(t) <= 30 and length_of_longest_ordered_sequence(t) >= k),
        timeout_after=60,
    )
    start = xs[0]
    assert xs == list(range(start, start + k))


def test_increasing_string_sequence():
    n = 7
    lb = '✐'
    xs = minimal(
        [text_type], lambda t: (
            n <= len(t) and
            all(t) and
            t[0] >= lb and
            t[-1] >= lb and
            length_of_longest_ordered_sequence(t) >= n
        ),
        timeout_after=30,
    )
    assert n <= len(xs) <= n + 2
    for i in hrange(len(xs) - 1):
        assert abs(len(xs[i + 1]) - len(xs[i])) <= 1


def test_small_sum_lists():
    xs = minimal(
        [float],
        lambda x:
            len(x) >= 100 and sum(t for t in x if float('inf') > t >= 0) >= 1,
        settings=Settings(average_list_length=200),
    )
    assert 1.0 <= sum(t for t in xs if t >= 0) <= 1.01


def test_increasing_float_sequence():
    xs = minimal(
        [float], lambda x: length_of_longest_ordered_sequence([
            t for t in x if t >= 0
        ]) >= 7 and len([t for t in x if t >= 500.0]) >= 4
    )
    assert max(xs) < 1000
    assert not any(math.isinf(x) for x in xs)


def test_increasing_integers_from_sequence():
    n = 6
    lb = 50000
    xs = minimal(
        [integers_from(0)], lambda t: (
            n <= len(t) and
            all(t) and
            any(s >= lb for s in t) and
            length_of_longest_ordered_sequence(t) >= n
        ),
        timeout_after=20,
    )
    assert n <= len(xs) <= n + 2


def test_find_large_union_list():
    def large_mostly_non_overlapping(xs):
        assume(xs)
        assume(all(xs))
        union = reduce(operator.or_, xs)
        return len(union) >= 30

    result = minimal([{int}], large_mostly_non_overlapping, timeout_after=30)
    union = reduce(operator.or_, result)
    assert len(union) == 30
    assert max(union) == min(union) + len(union) - 1
    for x in result:
        for y in result:
            if x is not y:
                assert not (x & y)


def test_anti_sorted_ordered_pair():
    result = minimal(
        [OrderedPair],
        lambda x: (
            len(x) >= 30 and
            2 < length_of_longest_ordered_sequence(x) <= 10))
    assert len(result) == 30


def test_constant_lists_of_diverse_length():
    # This does not currently work very well. We delete, but we don't actually
    # get all that far with simplification of the individual elements.
    result = minimal(
        [constant_list(int)], lambda x: len(set(map(len, x))) >= 20,
        timeout_after=30,
    )

    assert len(result) == 20


def test_finds_non_reversible_floats():
    t = minimal(
        [float], lambda xs: sum(xs) != sum(reversed(xs)),
        timeout_after=20,
    )
    assert len(t) <= 10
