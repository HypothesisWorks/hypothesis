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

import sys
import math
import operator
from random import Random
from decimal import Decimal
from fractions import Fraction

import pytest
from flaky import flaky

from hypothesis import find, given, assume, example, settings
from tests.common import parametrize, ordered_pair, constant_list
from hypothesis.strategies import just, sets, text, lists, binary, \
    floats, tuples, randoms, booleans, decimals, integers, fractions, \
    recursive, frozensets, dictionaries, sampled_from, random_module
from hypothesis.internal.debug import minimal
from hypothesis.internal.compat import PY3, hrange, reduce, Counter, \
    OrderedDict, integer_types

slightly_flaky = flaky(min_passes=1, max_runs=3)


@slightly_flaky
def test_minimize_list_on_large_structure():
    def test_list_in_range(xs):
        return len([
            x for x in xs
            if x >= 10
        ]) >= 60

    assert minimal(
        lists(integers(), min_size=60, average_size=120), test_list_in_range,
        timeout_after=30,
    ) == [10] * 60


@flaky(min_passes=1, max_runs=4)
def test_minimize_list_of_sets_on_large_structure():
    def test_list_in_range(xs):
        return len(list(filter(None, xs))) >= 30

    x = minimal(
        lists(frozensets(integers()), min_size=30), test_list_in_range,
        timeout_after=20,
    )

    assert x == [frozenset([0])] * 30


def test_integers_from_minimizes_leftwards():
    assert minimal(integers(min_value=101)) == 101


def test_minimal_fractions_1():
    assert minimal(fractions()) == Fraction(0)


def test_minimal_fractions_2():
    assert minimal(fractions(), lambda x: x >= 1) == Fraction(1)


def test_minimal_fractions_3():
    assert minimal(
        lists(fractions()), lambda s: len(s) >= 20) == [Fraction(0)] * 20


@slightly_flaky
def test_minimal_fractions_4():
    x = minimal(
        lists(fractions(), min_size=20),
        lambda s: len([t for t in s if t >= 1]) >= 20
    )
    assert x == [Fraction(1)] * 20


def test_minimize_list_of_floats_on_large_structure():
    def test_list_in_range(xs):
        return len([
            x for x in xs
            if x >= 3
        ]) >= 30

    result = minimal(
        lists(floats(), min_size=50, average_size=100),
        test_list_in_range, timeout_after=20)
    result.sort()
    assert result == [0.0] * 20 + [3.0] * 30


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
    size = 15
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


@pytest.mark.parametrize(
    (u'string',), [(text(),), (binary(),)],
    ids=[u'text', u'binary()']
)
def test_minimal_unsorted_strings(string):
    def dedupe(xs):
        result = []
        for x in xs:
            if x not in result:
                result.append(x)
        return result

    result = minimal(
        lists(string).map(dedupe),
        lambda xs: assume(len(xs) >= 5) and sorted(xs) != xs
    )
    assert len(result) == 5
    for ex in result:
        if len(ex) > 1:
            for i in hrange(len(ex)):
                assert ex[:i] in result


@slightly_flaky
def test_finds_list_with_plenty_duplicates():
    def is_good(xs):
        return max(Counter(xs).values()) >= 3

    result = minimal(
        lists(text(min_size=1), average_size=50, min_size=1), is_good,
        timeout_after=20,
    )
    assert result == [u'0'] * 3


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

    assert minimal(
        lists(booleans() | tuples(integers()), min_size=50),
        long_list_with_enough_bools
    ) == [False] * 50


def test_tuples_do_not_block_cloning():
    assert minimal(
        lists(tuples(booleans() | tuples(integers())), min_size=50),
        lambda x: any(isinstance(t[0], bool) for t in x),
        timeout_after=60,
    ) == [(False,)] * 50


def test_can_simplify_flatmap_with_bounded_left_hand_size():
    assert minimal(
        booleans().flatmap(lambda x: lists(just(x))),
        lambda x: len(x) >= 10) == [False] * 10


def test_can_simplify_across_flatmap_of_just():
    assert minimal(integers().flatmap(just)) == 0


def test_can_simplify_on_right_hand_strategy_of_flatmap():
    assert minimal(integers().flatmap(lambda x: lists(just(x)))) == []


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
            assume(len(x) >= 20) and all(x[i] >= target[i] for i in target))
    )
    assert x == target


def test_minimize_one_of_distinct_types():
    y = booleans() | binary()
    x = minimal(
        tuples(y, y),
        lambda x: type(x[0]) != type(x[1])
    )
    assert x in (
        (False, b''),
        (b'', False)
    )


@pytest.mark.skipif(PY3, reason=u'Python 3 has better integers')
def test_minimize_long():
    assert minimal(
        integers(), lambda x: type(x).__name__ == u'long') == sys.maxint + 1


def test_non_reversible_ints_as_decimals():
    def not_reversible(xs):
        ts = list(map(Decimal, xs))
        return sum(ts) != sum(reversed(ts))

    sigh = minimal(lists(integers()), not_reversible, timeout_after=30)
    assert len(sigh) <= 25


def test_non_reversible_fractions_as_decimals():
    def not_reversible(xs):
        xs = [Decimal(x.numerator) / x.denominator for x in xs]
        return sum(xs) != sum(reversed(xs))

    sigh = minimal(lists(fractions()), not_reversible, timeout_after=20)
    assert len(sigh) <= 25


def test_non_reversible_decimals():
    def not_reversible(xs):
        assume(all(x.is_finite() for x in xs))
        return sum(xs) != sum(reversed(xs))
    sigh = minimal(lists(decimals()), not_reversible, timeout_after=30)
    assert len(sigh) <= 25


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


def test_increasing_integer_sequence():
    k = 6
    xs = minimal(
        lists(integers()), lambda t: (
            len(t) <= 30 and length_of_longest_ordered_sequence(t) >= k),
        timeout_after=60,
    )
    start = xs[0]
    assert xs == list(range(start, start + k))


def test_increasing_string_sequence():
    n = 7
    lb = u'✐'
    xs = minimal(
        lists(text(min_size=1), min_size=n, average_size=50), lambda t: (
            t[0] >= lb and
            t[-1] >= lb and
            length_of_longest_ordered_sequence(t) >= n
        ),
        timeout_after=30,
    )
    assert n <= len(xs) <= n + 2
    for i in hrange(len(xs) - 1):
        assert abs(len(xs[i + 1]) - len(xs[i])) <= 1


def test_decreasing_string_sequence():
    n = 7
    lb = u'✐'
    xs = minimal(
        lists(text(min_size=1), min_size=n, average_size=50), lambda t: (
            n <= len(t) and
            all(t) and
            t[0] >= lb and
            t[-1] >= lb and
            length_of_longest_ordered_sequence(list(reversed(t))) >= n
        ),
        timeout_after=30,
    )
    assert n <= len(xs) <= n + 2
    for i in hrange(len(xs) - 1):
        assert abs(len(xs[i + 1]) - len(xs[i])) <= 1


def test_small_sum_lists():
    xs = minimal(
        lists(floats(), min_size=100, average_size=200),
        lambda x:
            sum(t for t in x if float(u'inf') > t >= 0) >= 1,
        timeout_after=60,
    )
    assert 1.0 <= sum(t for t in xs if t >= 0) <= 1.5


def test_increasing_float_sequence():
    xs = minimal(
        lists(floats()), lambda x: length_of_longest_ordered_sequence([
            t for t in x if t >= 0
        ]) >= 7 and len([t for t in x if t >= 500.0]) >= 4
    )
    assert max(xs) < 1000
    assert not any(math.isinf(x) for x in xs)


def test_increasing_integers_from_sequence():
    n = 6
    lb = 50000
    xs = minimal(
        lists(integers(min_value=0)), lambda t: (
            n <= len(t) and
            all(t) and
            any(s >= lb for s in t) and
            length_of_longest_ordered_sequence(t) >= n
        ),
        timeout_after=60,
    )
    assert n <= len(xs) <= n + 2


def test_find_large_union_list():
    def large_mostly_non_overlapping(xs):
        assume(xs)
        assume(all(xs))
        union = reduce(operator.or_, xs)
        return len(union) >= 30

    result = minimal(
        lists(sets(integers())),
        large_mostly_non_overlapping, timeout_after=60)
    union = reduce(operator.or_, result)
    assert len(union) == 30
    assert max(union) == min(union) + len(union) - 1
    for x in result:
        for y in result:
            if x is not y:
                assert not (x & y)


def test_anti_sorted_ordered_pair():
    result = minimal(
        lists(ordered_pair),
        lambda x: (
            len(x) >= 30 and
            2 < length_of_longest_ordered_sequence(x) <= 10))
    assert len(result) == 30


def test_constant_lists_of_diverse_length():
    # This does not currently work very well. We delete, but we don't actually
    # get all that far with simplification of the individual elements.
    result = minimal(
        lists(constant_list(integers())),
        lambda x: len(set(map(len, x))) >= 20,
        timeout_after=30,
    )
    assert len(result) == 20


def test_finds_non_reversible_floats():
    t = minimal(
        lists(floats()), lambda xs:
            not math.isnan(sum(xs)) and sum(xs) != sum(reversed(xs)),
        timeout_after=40,
        settings=settings(database=None)
    )
    assert len(repr(t)) <= 200
    print(t)


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


def test_unique_lists_of_single_characters():
    x = minimal(
        lists(text(max_size=1), unique=True, min_size=5)
    )
    assert sorted(x) == ['', '0', '1', '2', '3']


@given(randoms())
@settings(max_examples=10, database=None, max_shrinks=0)
@example(rnd=Random(340282366920938463462798146679426884207))
def test_can_simplify_hard_recursive_data_into_boolean_alternative(rnd):
    """This test forces us to exercise the simplification through redrawing
    functionality, thus testing that we can deal with bad templates."""
    def leaves(ls):
        if isinstance(ls, (bool,) + integer_types):
            return [ls]
        else:
            return sum(map(leaves, ls), [])

    def hard(base):
        return recursive(
            base, lambda x: lists(x, max_size=5), max_leaves=20)
    r = find(
        hard(booleans()) |
        hard(booleans()) |
        hard(booleans()) |
        hard(integers()) |
        hard(booleans()),
        lambda x:
            len(leaves(x)) >= 3 and
            any(isinstance(t, bool) for t in leaves(x)),
        random=rnd, settings=settings(
            database=None, max_examples=5000, max_shrinks=1000))
    lvs = leaves(r)
    assert lvs == [False] * 3
    assert all(isinstance(v, bool) for v in lvs), repr(lvs)


def test_can_clone_same_length_items():
    ls = find(
        lists(frozensets(integers(), min_size=10, max_size=10)),
        lambda x: len(x) >= 20
    )
    assert len(set(ls)) == 1


@given(random_module(), integers(min_value=0))
@example(None, 62677)
@settings(max_examples=100, max_shrinks=0)
def test_minimize_down_to(rnd, i):
    j = find(
        integers(), lambda x: x >= i,
        settings=settings(max_examples=1000, database=None, max_shrinks=1000))
    assert i == j


@flaky(max_runs=2, min_passes=1)
def test_can_find_quite_deep_lists():
    def depth(x):
        if x and isinstance(x, list):
            return 1 + max(map(depth, x))
        else:
            return 1

    deep = find(
        recursive(booleans(), lambda x: lists(x, max_size=3)),
        lambda x: depth(x) >= 5)
    assert deep == [[[[False]]]]
