# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from collections import Counter

import pytest

from hypothesis import HealthCheck, assume, given, settings
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.strategies import (
    booleans,
    builds,
    floats,
    integers,
    just,
    lists,
    text,
    tuples,
)

from tests.common.debug import find_any, minimal
from tests.common.utils import Why, xfail_on_crosshair

ConstantLists = integers().flatmap(lambda i: lists(just(i)))

OrderedPairs = integers(1, 200).flatmap(lambda e: tuples(integers(0, e - 1), just(e)))


# This health check fails very very occasionally - rarely enough to not be worth
# investigation
@settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
@given(ConstantLists)
def test_constant_lists_are_constant(x):
    assume(len(x) >= 3)
    assert len(set(x)) == 1


@settings(max_examples=100)
@given(OrderedPairs)
def test_in_order(x):
    assert x[0] < x[1]


@xfail_on_crosshair(
    Why.undiscovered
)  # (SampledFromStrategy.calc_label() hashes a symbolic float)
def test_flatmap_retrieve_from_db():
    track = []

    @given(floats(0, 1).flatmap(lambda x: lists(just(x))))
    @settings(database=InMemoryExampleDatabase())
    def record_and_test_size(xs):
        if sum(xs) >= 1:
            track.append(xs)
            raise AssertionError

    with pytest.raises(AssertionError):
        record_and_test_size()

    assert track
    example = track[-1]
    track = []

    with pytest.raises(AssertionError):
        record_and_test_size()

    assert track[0] == example


def test_flatmap_does_not_reuse_strategies():
    s = builds(list).flatmap(just)
    assert find_any(s) is not find_any(s)


def test_flatmap_has_original_strategy_repr():
    ints = integers()
    ints_up = ints.flatmap(lambda n: integers(min_value=n))
    assert repr(ints) in repr(ints_up)


@pytest.mark.skipif(
    settings._current_profile == "crosshair",
    reason="takes ~6 mins in CI, but ~7 sec in isolation. Unsure why",
)
def test_mixed_list_flatmap():
    s = lists(booleans().flatmap(lambda b: booleans() if b else text()))

    def criterion(ls):
        c = Counter(type(l) for l in ls)
        return len(c) >= 2 and min(c.values()) >= 3

    result = minimal(s, criterion)
    assert len(result) == 6
    assert set(result) == {False, ""}


@xfail_on_crosshair(Why.undiscovered)  # for n >= 8 at least
@pytest.mark.parametrize("n", range(1, 10))
def test_can_shrink_through_a_binding(n):
    bool_lists = integers(0, 100).flatmap(
        lambda k: lists(booleans(), min_size=k, max_size=k)
    )
    assert minimal(bool_lists, lambda x: x.count(True) >= n) == [True] * n


@xfail_on_crosshair(Why.undiscovered)  # for n >= 8 at least
@pytest.mark.parametrize("n", range(1, 10))
def test_can_delete_in_middle_of_a_binding(n):
    bool_lists = integers(1, 100).flatmap(
        lambda k: lists(booleans(), min_size=k, max_size=k)
    )
    result = minimal(bool_lists, lambda x: x[0] and x[-1] and x.count(False) >= n)
    assert result == [True] + [False] * n + [True]
