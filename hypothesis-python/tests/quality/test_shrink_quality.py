# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

from collections import OrderedDict, namedtuple
from fractions import Fraction
from functools import reduce

import pytest

from hypothesis import assume, settings
from hypothesis.internal.compat import hrange
from hypothesis.strategies import (
    booleans,
    builds,
    dictionaries,
    fixed_dictionaries,
    fractions,
    frozensets,
    integers,
    just,
    lists,
    none,
    sampled_from,
    sets,
    text,
    tuples,
)
from tests.common.debug import minimal
from tests.common.utils import flaky


def test_integers_from_minimizes_leftwards():
    assert minimal(integers(min_value=101)) == 101


def test_minimal_fractions_1():
    assert minimal(fractions()) == Fraction(0)


def test_minimal_fractions_2():
    assert minimal(fractions(), lambda x: x >= 1) == Fraction(1)


def test_minimal_fractions_3():
    assert minimal(lists(fractions()), lambda s: len(s) >= 5) == [Fraction(0)] * 5


def test_minimize_string_to_empty():
    assert minimal(text()) == u""


def test_minimize_one_of():
    for _ in hrange(100):
        assert minimal(integers() | text() | booleans()) in (0, u"", False)


def test_minimize_mixed_list():
    mixed = minimal(lists(integers() | text()), lambda x: len(x) >= 10)
    assert set(mixed).issubset({0, u""})


def test_minimize_longer_string():
    assert minimal(text(), lambda x: len(x) >= 10) == u"0" * 10


def test_minimize_longer_list_of_strings():
    assert minimal(lists(text()), lambda x: len(x) >= 10) == [u""] * 10


def test_minimize_3_set():
    assert minimal(sets(integers()), lambda x: len(x) >= 3) in ({0, 1, 2}, {-1, 0, 1})


def test_minimize_3_set_of_tuples():
    assert minimal(sets(tuples(integers())), lambda x: len(x) >= 2) == {(0,), (1,)}


def test_minimize_sets_of_sets():
    elements = integers(1, 100)
    size = 8
    set_of_sets = minimal(sets(frozensets(elements), min_size=size))
    assert frozenset() in set_of_sets
    assert len(set_of_sets) == size
    for s in set_of_sets:
        if len(s) > 1:
            assert any(s != t and t.issubset(s) for t in set_of_sets)


def test_can_simplify_flatmap_with_bounded_left_hand_size():
    assert (
        minimal(booleans().flatmap(lambda x: lists(just(x))), lambda x: len(x) >= 10)
        == [False] * 10
    )


def test_can_simplify_across_flatmap_of_just():
    assert minimal(integers().flatmap(just)) == 0


def test_can_simplify_on_right_hand_strategy_of_flatmap():
    assert minimal(integers().flatmap(lambda x: lists(just(x)))) == []


@flaky(min_passes=5, max_runs=5)
def test_can_ignore_left_hand_side_of_flatmap():
    assert (
        minimal(integers().flatmap(lambda x: lists(integers())), lambda x: len(x) >= 10)
        == [0] * 10
    )


def test_can_simplify_on_both_sides_of_flatmap():
    assert (
        minimal(integers().flatmap(lambda x: lists(just(x))), lambda x: len(x) >= 10)
        == [0] * 10
    )


def test_flatmap_rectangles():
    lengths = integers(min_value=0, max_value=10)

    def lists_of_length(n):
        return lists(sampled_from("ab"), min_size=n, max_size=n)

    xs = minimal(
        lengths.flatmap(lambda w: lists(lists_of_length(w))),
        lambda x: ["a", "b"] in x,
        settings=settings(database=None, max_examples=2000),
    )
    assert xs == [["a", "b"]]


@flaky(min_passes=5, max_runs=5)
@pytest.mark.parametrize("dict_class", [dict, OrderedDict])
def test_dictionary(dict_class):
    assert (
        minimal(dictionaries(keys=integers(), values=text(), dict_class=dict_class))
        == dict_class()
    )

    x = minimal(
        dictionaries(keys=integers(), values=text(), dict_class=dict_class),
        lambda t: len(t) >= 3,
    )
    assert isinstance(x, dict_class)
    assert set(x.values()) == {u""}
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
    x = minimal(lists(ir), lambda x: len(x) >= 20, timeout_after=20)
    assert x == desired_result


def test_minimize_multiple_elements_in_silly_large_int_range_min_is_not_dupe():
    ir = integers(0, 2 ** 256)
    target = list(range(20))

    x = minimal(
        lists(ir),
        lambda x: (assume(len(x) >= 20) and all(x[i] >= target[i] for i in target)),
        timeout_after=60,
    )
    assert x == target


def test_find_large_union_list():
    size = 10

    def large_mostly_non_overlapping(xs):
        union = reduce(set.union, xs)
        return len(union) >= size

    result = minimal(
        lists(sets(integers(), min_size=1), min_size=1),
        large_mostly_non_overlapping,
        timeout_after=120,
    )
    assert len(result) == 1
    union = reduce(set.union, result)
    assert len(union) == size
    assert max(union) == min(union) + len(union) - 1


@pytest.mark.parametrize("n", [0, 1, 10, 100, 1000])
@pytest.mark.parametrize(
    "seed", [13878544811291720918, 15832355027548327468, 12901656430307478246]
)
def test_containment(n, seed):
    iv = minimal(
        tuples(lists(integers()), integers()),
        lambda x: x[1] in x[0] and x[1] >= n,
        timeout_after=60,
    )
    assert iv == ([n], n)


@pytest.mark.parametrize("n", [0, 1, 2])
def test_text_containment(n):
    iv = minimal(
        tuples(lists(text()), text()),
        lambda x: x[1] in x[0] and len(x[1]) >= n,
        timeout_after=60,
    )

    value = "0" * n

    assert iv == ([value], value)


def test_duplicate_containment():
    ls, i = minimal(
        tuples(lists(integers()), integers()),
        lambda s: s[0].count(s[1]) > 1,
        timeout_after=100,
    )
    assert ls == [0, 0]
    assert i == 0


@pytest.mark.parametrize("seed", [11, 28, 37])
def test_reordering_bytes(seed):
    ls = minimal(lists(integers()), lambda x: sum(x) >= 10 and len(x) >= 3)
    assert ls == sorted(ls)


def test_minimize_long_list():
    assert (
        minimal(lists(booleans(), min_size=50), lambda x: len(x) >= 70) == [False] * 70
    )


def test_minimize_list_of_longish_lists():
    size = 5
    xs = minimal(
        lists(lists(booleans())),
        lambda x: len([t for t in x if any(t) and len(t) >= 2]) >= size,
    )
    assert len(xs) == size
    for x in xs:
        assert x == [False, True]


def test_minimize_list_of_fairly_non_unique_ints():
    xs = minimal(lists(integers()), lambda x: len(set(x)) < len(x))
    assert len(xs) == 2


def test_list_with_complex_sorting_structure():
    xs = minimal(
        lists(lists(booleans())),
        lambda x: [list(reversed(t)) for t in x] > x and len(x) > 3,
    )
    assert len(xs) == 4


def test_list_with_wide_gap():
    xs = minimal(lists(integers()), lambda x: x and (max(x) > min(x) + 10 > 0))
    assert len(xs) == 2
    xs.sort()
    assert xs[1] == 11 + xs[0]


def test_minimize_namedtuple():
    T = namedtuple(u"T", (u"a", u"b"))
    tab = minimal(builds(T, integers(), integers()), lambda x: x.a < x.b)
    assert tab.b == tab.a + 1


def test_minimize_dict():
    tab = minimal(
        fixed_dictionaries({u"a": booleans(), u"b": booleans()}),
        lambda x: x[u"a"] or x[u"b"],
    )
    assert not (tab[u"a"] and tab[u"b"])


def test_minimize_list_of_sets():
    assert minimal(
        lists(sets(booleans())), lambda x: len(list(filter(None, x))) >= 3
    ) == ([{False}] * 3)


def test_minimize_list_of_lists():
    assert minimal(
        lists(lists(integers())), lambda x: len(list(filter(None, x))) >= 3
    ) == ([[0]] * 3)


def test_minimize_list_of_tuples():
    xs = minimal(lists(tuples(integers(), integers())), lambda x: len(x) >= 2)
    assert xs == [(0, 0), (0, 0)]


def test_minimize_multi_key_dicts():
    assert minimal(dictionaries(keys=booleans(), values=booleans()), bool) == {
        False: False
    }


def test_multiple_empty_lists_are_independent():
    x = minimal(lists(lists(none(), max_size=0)), lambda t: len(t) >= 2)
    u, v = x
    assert u is not v


def test_can_find_sets_unique_by_incomplete_data():
    size = 5
    ls = minimal(
        lists(tuples(integers(), integers()), unique_by=max), lambda x: len(x) >= size
    )
    assert len(ls) == size
    values = sorted(map(max, ls))
    assert values[-1] - values[0] == size - 1
    for u, _ in ls:
        assert u <= 0


@pytest.mark.parametrize(u"n", range(10))
def test_lists_forced_near_top(n):
    assert minimal(
        lists(integers(), min_size=n, max_size=n + 2), lambda t: len(t) == n + 2
    ) == [0] * (n + 2)
