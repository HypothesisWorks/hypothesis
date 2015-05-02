# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis.internal.compat import hrange


def test_small_hrange():
    assert list(hrange(5)) == [0, 1, 2, 3, 4]
    assert list(hrange(3, 5)) == [3, 4]
    assert list(hrange(1, 10, 2)) == [1, 3, 5, 7, 9]


def test_large_hrange():
    n = 1 << 1024
    assert list(hrange(n, n + 5, 2)) == [n, n + 2, n + 4]
