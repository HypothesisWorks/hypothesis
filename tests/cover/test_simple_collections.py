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

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from random import Random
from itertools import islice
from collections import namedtuple

import pytest
from hypothesis import Settings, find, given, strategy
from hypothesis.strategies import sets, lists, builds, tuples, booleans, \
    integers, frozensets, dictionaries, complex_numbers, \
    fixed_dictionaries

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict


@pytest.mark.parametrize(('col', 'strat'), [
    ((), tuples()),
    ([], lists(max_size=0)),
    (set(), sets(max_size=0)),
    (frozenset(), frozensets(max_size=0)),
    ({}, fixed_dictionaries({})),
])
def test_find_empty_collection_gives_empty(col, strat):
    assert find(strat, lambda x: True) == col


@pytest.mark.parametrize(('coltype', 'strat'), [
    (list, lists),
    (set, sets),
    (frozenset, frozensets),
])
def test_find_non_empty_collection_gives_single_zero(coltype, strat):
    assert find(
        strat(integers()), bool
    ) == coltype((0,))


@pytest.mark.parametrize(('coltype', 'strat'), [
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
    assert find(lists(booleans()), lambda x: len(x) >= 70) == [False] * 70


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
    T = namedtuple('T', ('a', 'b'))
    tab = find(
        builds(T, integers(), integers()),
        lambda x: x.a < x.b)
    assert tab.b == tab.a + 1


def test_minimize_dict():
    tab = find(
        fixed_dictionaries({'a': booleans(), 'b': booleans()}),
        lambda x: x['a'] or x['b']
    )
    assert not (tab['a'] and tab['b'])


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
        fixed_dictionaries({1: booleans(), 'hi': lists(booleans())}),
        lambda x: True
    ) == {1: False, 'hi': []}


def test_deeply_nested_sets():
    def f(n):
        if n <= 0:
            return booleans()
        return sets(f(n - 1))

    assert strategy(f(10)).template_upper_bound == float('inf')


def test_list_simplicity():
    # Testing internal details because this is too damn hard to hit reliably
    s = lists(booleans())

    assert not s.strictly_simpler((), ())
    assert s.strictly_simpler((), (False,))
    assert not s.strictly_simpler((True,), ())
    assert s.strictly_simpler((True,), (False, True))
    assert s.strictly_simpler((False,), (True,))
    assert not s.strictly_simpler((True,), (False,))
    assert s.strictly_simpler((False, False,), (False, True))
    assert not s.strictly_simpler((False, True), (False, True))


def test_nested_set_complexity():
    strat = frozensets(frozensets(complex_numbers()))

    rnd = Random(0)
    template = (
        ((float('inf'), 1.0), (-1.0325215252103651e-149, 1.0)),
        ((-1.677443578786644e-309, -1.0), (-2.2250738585072014e-308, 0.0))
    )
    simplifiers = list(strat.simplifiers(rnd, template))
    rnd.shuffle(simplifiers)
    simplifiers = simplifiers[:10]
    for simplify in simplifiers:
        for s in islice(simplify(rnd, template), 50):
            assert not strat.strictly_simpler(template, s)


def test_multiple_empty_lists_are_independent():
    x = find(lists(lists(max_size=0)), lambda t: len(t) >= 2)
    u, v = x
    assert u is not v


@given(sets(integers(0, 100), min_size=2, max_size=10), settings=Settings(
    max_examples=100
))
def test_sets_are_size_bounded(xs):
    assert 2 <= len(xs) <= 10


def test_ordered_dictionaries_preserve_keys():
    r = Random()
    keys = list(range(100))
    r.shuffle(keys)
    x = fixed_dictionaries(
        OrderedDict([(k, booleans()) for k in keys])).example()
    assert list(x.keys()) == keys


@pytest.mark.parametrize('n', range(10))
def test_lists_of_fixed_length(n):
    assert find(
        lists(integers(), min_size=n, max_size=n), lambda x: True) == [0] * n


@pytest.mark.parametrize('n', range(10))
def test_sets_of_fixed_length(n):
    x = find(
        sets(integers(), min_size=n, max_size=n), lambda x: True)

    if not n:
        assert x == set()
    else:
        assert x == set(range(min(x), min(x) + n))


@pytest.mark.parametrize('n', range(10))
def test_dictionaries_of_fixed_length(n):
    x = set(find(
        dictionaries(integers(), booleans(), min_size=n, max_size=n),
        lambda x: True).keys())

    if not n:
        assert x == set()
    else:
        assert x == set(range(min(x), min(x) + n))


@pytest.mark.parametrize('n', range(10))
def test_lists_of_lower_bounded_length(n):
    x = find(
        lists(integers(), min_size=n), lambda x: sum(x) >= 2 * n
    )
    assert n <= len(x) <= 2 * n
    assert all(t >= 0 for t in x)
    assert len(x) == n or all(t > 0 for t in x)
    assert sum(x) == 2 * n


@pytest.mark.parametrize('n', range(10))
def test_lists_forced_near_top(n):
    assert find(
        lists(integers(), min_size=n, max_size=n + 2),
        lambda t: len(t) == n + 2
    ) == [0] * (n + 2)


def test_cloning_is_a_no_op_on_short_lists():
    s = lists(booleans()).wrapped_strategy
    assert list(s.simplify_with_example_cloning(Random(), (False,))) == []
