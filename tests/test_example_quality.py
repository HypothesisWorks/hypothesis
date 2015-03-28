# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from collections import Counter

import pytest
from hypothesis import Settings, given, assume, strategy
from tests.common import timeout
from hypothesis.core import _debugging_return_failing_example
from hypothesis.specifiers import one_of
from hypothesis.internal.compat import hrange, text_type, binary_type

quality_settings = Settings(
    max_examples=5000
)


def minimal(definition, condition=None):
    @timeout(5)
    @given(definition, settings=quality_settings)
    def everything_is_terrible(x):
        if condition is None:
            assert False
        else:
            assert not condition(x)

    with _debugging_return_failing_example.with_value(True):
        result = everything_is_terrible()
        assert result is not None
        return result[1]['x']


def test_minimize_list_to_empty():
    assert minimal([int]) == []


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
    assert minimal({int}, lambda x: len(x) >= 3) == {0, 1, 2}


def test_minimize_3_set_of_tuples():
    assert minimal({(int,)}, lambda x: len(x) >= 2) == {(0,), (1,)}


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
        xs = filter(None, xs)
        assume(xs)
        return max(Counter(xs).values()) >= 3

    result = minimal(
        [str], is_good
    )
    assert len(result) == 3
    assert len(set(result)) == 1
    assert len(result[0]) == 1
