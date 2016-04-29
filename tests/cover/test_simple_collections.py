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

from random import Random
from collections import namedtuple

import pytest
from flaky import flaky

from hypothesis import find, given, settings
from hypothesis.strategies import sets, text, lists, builds, tuples, \
    booleans, integers, frozensets, dictionaries, fixed_dictionaries
from hypothesis.internal.debug import minimal
from hypothesis.internal.compat import OrderedDict


@pytest.mark.parametrize((u'col', u'strat'), [
    ((), tuples()),
    ([], lists(max_size=0)),
    (set(), sets(max_size=0)),
    (frozenset(), frozensets(max_size=0)),
    ({}, fixed_dictionaries({})),
])
def test_find_empty_collection_gives_empty(col, strat):
    assert find(strat, lambda x: True) == col


@pytest.mark.parametrize((u'coltype', u'strat'), [
    (list, lists),
    (set, sets),
    (frozenset, frozensets),
])
def test_find_non_empty_collection_gives_single_zero(coltype, strat):
    assert find(
        strat(integers()), bool
    ) == coltype((0,))


@pytest.mark.parametrize((u'coltype', u'strat'), [
    (list, lists),
    (set, sets),
    (frozenset, frozensets),
])
def test_minimizes_to_empty(coltype, strat):
    assert find(
        strat(integers()), lambda x: True
    ) == coltype()


def test_minimizes_list_of_lists():
    xs = find(lists(lists(booleans())), lambda x: any(x) and not all(x))
    xs.sort()
    assert xs == [[], [False]]


def test_minimize_long_list():
    assert find(
        lists(booleans(), average_size=100), lambda x: len(x) >= 70
    ) == [False] * 70


def test_minimize_list_of_longish_lists():
    xs = find(
        lists(lists(booleans())),
        lambda x: len([t for t in x if any(t) and len(t) >= 3]) >= 10)
    assert len(xs) == 10
    for x in xs:
        assert len(x) == 3
        assert len([t for t in x if t]) == 1


def test_minimize_list_of_fairly_non_unique_ints():
    xs = find(lists(integers()), lambda x: len(set(x)) < len(x))
    assert len(xs) == 2


def test_list_with_complex_sorting_structure():
    xs = find(
        lists(lists(booleans())),
        lambda x: [list(reversed(t)) for t in x] > x and len(x) > 3)
    assert len(xs) == 4


def test_list_with_wide_gap():
    xs = find(lists(integers()), lambda x: x and (max(x) > min(x) + 10 > 0))
    assert len(xs) == 2
    xs.sort()
    assert xs[1] == 11 + xs[0]


def test_minimize_namedtuple():
    T = namedtuple(u'T', (u'a', u'b'))
    tab = find(
        builds(T, integers(), integers()),
        lambda x: x.a < x.b)
    assert tab.b == tab.a + 1


def test_minimize_dict():
    tab = find(
        fixed_dictionaries({u'a': booleans(), u'b': booleans()}),
        lambda x: x[u'a'] or x[u'b']
    )
    assert not (tab[u'a'] and tab[u'b'])


def test_minimize_list_of_sets():
    assert find(
        lists(sets(booleans())),
        lambda x: len(list(filter(None, x))) >= 3) == (
        [set((False,))] * 3
    )


def test_minimize_list_of_lists():
    assert find(
        lists(lists(integers())),
        lambda x: len(list(filter(None, x))) >= 3) == (
        [[0]] * 3
    )


def test_minimize_list_of_tuples():
    xs = find(
        lists(tuples(integers(), integers())), lambda x: len(x) >= 2)
    assert xs == [(0, 0), (0, 0)]


def test_minimize_multi_key_dicts():
    assert find(
        dictionaries(keys=booleans(), values=booleans()),
        bool
    ) == {False: False}


def test_minimize_dicts_with_incompatible_keys():
    assert find(
        fixed_dictionaries({1: booleans(), u'hi': lists(booleans())}),
        lambda x: True
    ) == {1: False, u'hi': []}


def test_multiple_empty_lists_are_independent():
    x = find(lists(lists(max_size=0)), lambda t: len(t) >= 2)
    u, v = x
    assert u is not v


@given(sets(integers(0, 100), min_size=2, max_size=10))
@settings(max_examples=100)
def test_sets_are_size_bounded(xs):
    assert 2 <= len(xs) <= 10


def test_ordered_dictionaries_preserve_keys():
    r = Random()
    keys = list(range(100))
    r.shuffle(keys)
    x = fixed_dictionaries(
        OrderedDict([(k, booleans()) for k in keys])).example()
    assert list(x.keys()) == keys


@pytest.mark.parametrize(u'n', range(10))
def test_lists_of_fixed_length(n):
    assert find(
        lists(integers(), min_size=n, max_size=n), lambda x: True) == [0] * n


@pytest.mark.parametrize(u'n', range(10))
def test_sets_of_fixed_length(n):
    x = find(
        sets(integers(), min_size=n, max_size=n), lambda x: True)
    assert len(x) == n

    if not n:
        assert x == set()
    else:
        assert x == set(range(min(x), min(x) + n))


@pytest.mark.parametrize(u'n', range(10))
def test_dictionaries_of_fixed_length(n):
    x = set(find(
        dictionaries(integers(), booleans(), min_size=n, max_size=n),
        lambda x: True).keys())

    if not n:
        assert x == set()
    else:
        assert x == set(range(min(x), min(x) + n))


@pytest.mark.parametrize(u'n', range(10))
def test_lists_of_lower_bounded_length(n):
    x = find(
        lists(integers(), min_size=n), lambda x: sum(x) >= 2 * n
    )
    assert n <= len(x) <= 2 * n
    assert all(t >= 0 for t in x)
    assert len(x) == n or all(t > 0 for t in x)
    assert sum(x) == 2 * n


@pytest.mark.parametrize(u'n', range(10))
def test_lists_forced_near_top(n):
    assert find(
        lists(integers(), min_size=n, max_size=n + 2),
        lambda t: len(t) == n + 2
    ) == [0] * (n + 2)


@flaky(max_runs=5, min_passes=1)
def test_can_find_unique_lists_of_non_set_order():
    ls = minimal(
        lists(text(), unique=True),
        lambda x: list(set(reversed(x))) != x
    )
    assert len(set(ls)) == len(ls)
    assert len(ls) == 2


def test_can_find_sets_unique_by_incomplete_data():
    ls = find(
        lists(lists(integers(min_value=0), min_size=2), unique_by=max),
        lambda x: len(x) >= 10
    )
    assert len(ls) == 10
    assert sorted(list(map(max, ls))) == list(range(10))
    for v in ls:
        assert 0 in v


def test_can_draw_empty_list_from_unsatisfiable_strategy():
    assert lists(integers().filter(lambda s: False)).example() == []


def test_can_draw_empty_set_from_unsatisfiable_strategy():
    assert sets(integers().filter(lambda s: False)).example() == set()
