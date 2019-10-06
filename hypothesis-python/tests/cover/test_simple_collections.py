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

from random import Random

import pytest

from hypothesis import given, settings
from hypothesis.internal.compat import OrderedDict
from hypothesis.strategies import (
    booleans,
    dictionaries,
    fixed_dictionaries,
    frozensets,
    integers,
    lists,
    none,
    nothing,
    sets,
    text,
    tuples,
)
from tests.common.debug import find_any, minimal
from tests.common.utils import flaky


@pytest.mark.parametrize(
    (u"col", u"strat"),
    [
        ((), tuples()),
        ([], lists(none(), max_size=0)),
        (set(), sets(none(), max_size=0)),
        (frozenset(), frozensets(none(), max_size=0)),
        ({}, fixed_dictionaries({})),
        ([], lists(nothing())),
        ([], lists(nothing(), unique=True)),
    ],
)
def test_find_empty_collection_gives_empty(col, strat):
    assert minimal(strat, lambda x: True) == col


@pytest.mark.parametrize(
    (u"coltype", u"strat"), [(list, lists), (set, sets), (frozenset, frozensets)]
)
def test_find_non_empty_collection_gives_single_zero(coltype, strat):
    assert minimal(strat(integers()), bool) == coltype((0,))


@pytest.mark.parametrize(
    (u"coltype", u"strat"), [(list, lists), (set, sets), (frozenset, frozensets)]
)
def test_minimizes_to_empty(coltype, strat):
    assert minimal(strat(integers()), lambda x: True) == coltype()


def test_minimizes_list_of_lists():
    xs = minimal(lists(lists(booleans())), lambda x: any(x) and not all(x))
    xs.sort()
    assert xs == [[], [False]]


@given(sets(integers(0, 100), min_size=2, max_size=10))
@settings(max_examples=100)
def test_sets_are_size_bounded(xs):
    assert 2 <= len(xs) <= 10


def test_ordered_dictionaries_preserve_keys():
    r = Random()
    keys = list(range(100))
    r.shuffle(keys)
    x = fixed_dictionaries(OrderedDict([(k, booleans()) for k in keys])).example()
    assert list(x.keys()) == keys


@pytest.mark.parametrize(u"n", range(10))
def test_lists_of_fixed_length(n):
    assert minimal(lists(integers(), min_size=n, max_size=n), lambda x: True) == [0] * n


@pytest.mark.parametrize(u"n", range(10))
def test_sets_of_fixed_length(n):
    x = minimal(sets(integers(), min_size=n, max_size=n), lambda x: True)
    assert len(x) == n

    if not n:
        assert x == set()
    else:
        assert x == set(range(min(x), min(x) + n))


@pytest.mark.parametrize(u"n", range(10))
def test_dictionaries_of_fixed_length(n):
    x = set(
        minimal(
            dictionaries(integers(), booleans(), min_size=n, max_size=n), lambda x: True
        ).keys()
    )

    if not n:
        assert x == set()
    else:
        assert x == set(range(min(x), min(x) + n))


@pytest.mark.parametrize(u"n", range(10))
def test_lists_of_lower_bounded_length(n):
    x = minimal(lists(integers(), min_size=n), lambda x: sum(x) >= 2 * n)
    assert n <= len(x) <= 2 * n
    assert all(t >= 0 for t in x)
    assert len(x) == n or all(t > 0 for t in x)
    assert sum(x) == 2 * n


@flaky(min_passes=1, max_runs=2)
def test_can_find_unique_lists_of_non_set_order():
    # This test checks that our strategy for unique lists doesn't accidentally
    # depend on the iteration order of sets.
    #
    # Unfortunately, that means that *this* test has to rely on set iteration
    # order. That makes it tricky to debug on CPython, because set iteration
    # order changes every time the process is launched.
    #
    # To get around this, define the PYTHONHASHSEED environment variable to
    # a consistent value. This could be 0, or it could be the PYTHONHASHSEED
    # value listed in a failure log from CI.

    ls = minimal(lists(text(), unique=True), lambda x: list(set(reversed(x))) != x)
    assert len(set(ls)) == len(ls)
    assert len(ls) == 2


def test_can_draw_empty_list_from_unsatisfiable_strategy():
    assert find_any(lists(integers().filter(lambda s: False))) == []


def test_can_draw_empty_set_from_unsatisfiable_strategy():
    assert find_any(sets(integers().filter(lambda s: False))) == set()


@given(lists(sets(none()), min_size=10))
def test_small_sized_sets(x):
    pass


def test_minimize_dicts_with_incompatible_keys():
    assert minimal(
        fixed_dictionaries({1: booleans(), u"hi": lists(booleans())}), lambda x: True
    ) == {1: False, u"hi": []}


@given(
    lists(
        tuples(integers(), integers()),
        min_size=2,
        unique_by=(lambda x: x[0], lambda x: x[1]),
    )
)
def test_lists_unique_by_tuple_funcs(ls):
    firstitems, seconditems = zip(*ls)
    assert len(set(firstitems)) == len(firstitems)
    assert len(set(seconditems)) == len(seconditems)
