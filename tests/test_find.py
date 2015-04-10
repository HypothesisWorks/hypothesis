# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import math

from hypothesis import find
from hypothesis.specifiers import streaming


def test_can_find_an_int():
    assert find(int, lambda x: True) == 0
    assert find(int, lambda x: x >= 13) == 13


def test_can_find_list():
    x = find([int], lambda x: sum(x) >= 10)
    assert sum(x) == 10


def test_can_find_nan():
    find(float, math.isnan)


def test_can_find_nans():
    x = find([float], lambda x: math.isnan(sum(x)))
    if len(x) == 1:
        assert math.isnan(x[0])
    else:
        assert len(x) == 2
        assert all(math.isinf(t) for t in x)


def test_find_large_structure():
    def test_list_in_range(xs):
        return len(list(filter(None, xs))) >= 50

    x = find([frozenset({int})], test_list_in_range)
    assert len(x) == 50
    assert len(set(x)) == 1


def test_find_streaming_int():
    n = 100
    r = find(streaming(int), lambda x: all(t >= 1 for t in x[:n]))
    assert list(r[:n]) == [1] * n
