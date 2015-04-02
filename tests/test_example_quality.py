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
from collections import Counter

import pytest
from hypothesis import Settings, given, assume, strategy
from tests.common import timeout
from hypothesis.core import _debugging_return_failing_example
from hypothesis.specifiers import one_of, integers_in_range
from hypothesis.internal.compat import hrange, text_type, binary_type

quality_settings = Settings(
    max_examples=5000
)


def minimal(definition, condition=None, settings=None):
    @timeout(5)
    @given(definition, settings=settings or quality_settings)
    def everything_is_terrible(x):
        if condition is None:
            assert False
        else:
            assert not condition(x)
    try:
        everything_is_terrible()
    except AssertionError:
        pass

    with _debugging_return_failing_example.with_value(True):
        result = everything_is_terrible()
        assert result is not None
        return result[1]['x']


def test_minimize_list_on_large_structure():
    def test_list_in_range(xs):
        assume(len(xs) >= 50)
        return len([
            x for x in xs
            if x >= 10
        ]) >= 70

    assert minimal([int], test_list_in_range) == [10] * 70


def test_minimize_list_of_sets_on_large_structure():
    def test_list_in_range(xs):
        assume(len(xs) >= 50)
        return len(list(filter(None, xs))) >= 50

    x = minimal([frozenset({int})], test_list_in_range)
    assert len(x) == 50
    assert len(set(x)) == 1


def test_shrinks_lists_to_small_pretty_quickly():

    shrunk = minimal(
        [str], lambda x: assume(len(x) >= 25) and len(set(x)) >= 10,
        settings=Settings(timeout=0.5))
    assert len(shrunk) == 25


def test_minimal_infinite_float_is_positive():
    assert minimal(float, math.isinf) == float('inf')

    def list_of_infinities(xs):
        assume(len(xs) >= 10)
        return len([
            t for t in xs if (math.isinf(t) or math.isnan(t))
        ]) >= 10

    assert minimal([float], list_of_infinities) == [float('inf')] * 10


def test_minimal_fractional_float():
    assert minimal(float, lambda x: x >= 1.5) in (1.5, 2.0)


def test_minimize_nan():
    assert math.isnan(minimal(float, math.isnan))


def test_minimize_very_large_float():
    t = sys.float_info.max / 2
    assert t <= minimal(float, lambda x: x >= t) < float('inf')


def test_list_of_fractional_float():
    assert set(minimal(
        [float], lambda x: len([t for t in x if t >= 1.5]) >= 10
    )) in (
        {1.5},
        {1.5, 2.0}
    )


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


def test_negative_floats_simplify_to_zero():
    assert minimal(float, lambda x: x <= -1.0) == -1.0


def test_minimize_list_to_empty():
    assert minimal([int]) == []


def test_minimize_string_to_empty():
    assert minimal(text_type) == ''


def test_minimize_one_of():
    for _ in hrange(100):
        assert minimal(one_of((int, str, bool))) in (
            0, '', False
        )


def test_minimize_negative_int():
    assert minimal(int, lambda x: x < 0) == -1


def test_positive_negative_int():
    assert minimal(int, lambda x: x > 0) == 1


boundaries = pytest.mark.parametrize('boundary', [0, 1, 11, 23, 64, 10000])


@boundaries
def test_minimizes_int_down_to_boundary(boundary):
    assert minimal(int, lambda x: x >= boundary) == boundary


@boundaries
def test_minimizes_int_up_to_boundary(boundary):
    assert minimal(int, lambda x: x <= -boundary) == -boundary


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


@pytest.mark.parametrize(('string',), [(text_type,), (binary_type,)])
def test_minimal_unsorted_strings(string):
    def dedupe(xs):
        result = []
        for x in xs:
            if x not in result:
                result.append(x)
        return result

    result = minimal(
        strategy([string]).map(dedupe),
        lambda xs: assume(len(xs) >= 10) and sorted(xs) != xs
    )
    assert len(result) == 10
    for example in result:
        if len(example) > 1:
            for i in hrange(len(example)):
                assert example[:i] in result


def test_finds_small_sum_large_lists():
    result = minimal(
        [int],
        lambda xs: assume(
            len(xs) >= 20 and all(x >= 0 for x in xs)) and sum(xs) < 150)
    assert result == [0] * 20


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
    assert minimal(
        [bool, (int,)],
        lambda x: len(x) >= 50 and any(isinstance(t, bool) for t in x)
    ) == [False] * 50


def test_tuples_do_not_block_cloning():
    assert minimal(
        [(one_of((bool, (int,))),)],
        lambda x: len(x) >= 50 and any(isinstance(t[0], bool) for t in x)
    ) == [(False,)] * 50
