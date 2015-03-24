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
from hypothesis import given, assume, strategy
from tests.common import timeout
from hypothesis.core import _debugging_return_failing_example
from hypothesis.internal.compat import text_type, binary_type


@pytest.mark.parametrize(('string',), [(text_type,), (binary_type,)])
def test_minimal_unsorted_strings(string):
    def dedupe(xs):
        result = []
        for x in xs:
            if x not in result:
                result.append(x)
        return result

    @timeout(10)
    @given(strategy([string]).map(dedupe))
    def is_sorted(xs):
        assume(len(xs) >= 10)
        assert sorted(xs) == xs

    with _debugging_return_failing_example.with_value(True):
        result = is_sorted()[1]['xs']
        assert len(result) == 10
        assert all(len(r) <= 2 for r in result)


def test_finds_small_sum_large_lists():
    @given([int])
    def small_sum_large_list(xs):
        assume(len(xs) >= 20)
        assume(all(x >= 0 for x in xs))
        assert sum(xs) >= 100

    with _debugging_return_failing_example.with_value(True):
        result = small_sum_large_list()[1]['xs']
        assert result == [0] * 20


def test_finds_list_with_plenty_duplicates():
    @given([str])
    def has_a_triple(xs):
        xs = list(filter(None, xs))
        assume(xs)
        c = Counter(xs)
        assert max(c.values()) < 3

    with _debugging_return_failing_example.with_value(True):
        result = has_a_triple()[1]['xs']
        assert len(result) == 3
        assert len(set(result)) == 1
        assert len(result[0]) == 1
