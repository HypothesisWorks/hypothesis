# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from collections import namedtuple

import pytest
from hypothesis import find, strategy
from hypothesis.specifiers import dictionary


@pytest.mark.parametrize('col', [
    (), [], set(), frozenset(), {},
])
def test_find_empty_collection_gives_empty(col):
    assert find(col, lambda x: True) == col


@pytest.mark.parametrize('coltype', [
    list, set, frozenset, tuple
])
def test_find_non_empty_collection_gives_single_zero(coltype):
    assert find(
        coltype((int,)), bool
    ) == coltype((0,))


@pytest.mark.parametrize('coltype', [
    list, set, frozenset,
])
def test_minimizes_to_empty(coltype):
    assert find(
        coltype((int,)), lambda x: True
    ) == coltype()


def test_minimizes_list_of_lists():
    xs = find([[bool]], lambda x: any(x) and not all(x))
    xs.sort()
    assert xs == [[], [False]]


def test_minimize_long_list():
    assert find([bool], lambda x: len(x) >= 70) == [False] * 70


def test_minimize_list_of_longish_lists():
    xs = find(
        [[bool]],
        lambda x: len([t for t in x if any(t) and len(t) >= 3]) >= 10)
    assert len(xs) == 10
    for x in xs:
        assert len(x) == 3
        assert len([t for t in x if t]) == 1


def test_minimize_list_of_fairly_non_unique_ints():
    xs = find([int], lambda x: len(set(x)) < len(x))
    assert len(xs) == 2


def test_list_with_complex_sorting_structure():
    xs = find(
        [[bool]],
        lambda x: [list(reversed(t)) for t in x] > x and len(x) > 3)
    assert len(xs) == 4


def test_list_with_wide_gap():
    xs = find([int], lambda x: x and (max(x) > min(x) + 10 > 0))
    assert len(xs) == 2
    xs.sort()
    assert xs[1] == 11 + xs[0]


def test_minimize_namedtuple():
    T = namedtuple('T', ('a', 'b'))
    tab = find(T(int, int), lambda x: x.a < x.b)
    assert tab.b == tab.a + 1


def test_minimize_dict():
    tab = find({'a': bool, 'b': bool}, lambda x: x['a'] or x['b'])
    assert not (tab['a'] and tab['b'])


def test_minimize_list_of_sets():
    assert find([{bool}], lambda x: len(list(filter(None, x))) >= 3) == (
        [{False}] * 3
    )


def test_minimize_list_of_lists():
    assert find([[int]], lambda x: len(list(filter(None, x))) >= 3) == (
        [[0]] * 3
    )


def test_minimize_list_of_tuples():
    xs = find([(int, int)], lambda x: len(x) >= 2)
    assert xs == [(0, 0), (0, 0)]


def test_minimize_multi_key_dicts():
    assert find(dictionary(bool, bool), bool) == {False: False}


def test_deeply_nested_sets():
    def f(n):
        if n <= 0:
            return bool
        return frozenset((f(n - 1),))

    assert strategy(f(10)).size_lower_bound == float('inf')


def test_list_simplicity():
    # Testing internal details because this is too damn hard to hit reliably
    s = strategy([bool])

    assert not s.strictly_simpler((), ())
    assert s.strictly_simpler((), (False,))
    assert not s.strictly_simpler((True,), ())
    assert s.strictly_simpler((True,), (False, True))
    assert s.strictly_simpler((False,), (True,))
    assert not s.strictly_simpler((True,), (False,))
    assert s.strictly_simpler((False, False,), (False, True))
    assert not s.strictly_simpler((False, True), (False, True))
