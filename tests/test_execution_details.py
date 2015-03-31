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

from hypothesis import given


def test_does_not_call_same_test_many_times():
    c = Counter()
    bad_example = []

    @given(int)
    def test_is_small(x):
        c[x] += 1
        if len(c) < 100:
            return

        if not bad_example:
            bad_example.append(x)
        if x == bad_example[0]:
            assert False

    try:
        test_is_small()
    except AssertionError:
        pass

    # Only the bad example should be used here.
    # One to falsify, one to verify it was not flaky, one on the final run
    assert [t for t in c.items() if t[1] > 1] == [(bad_example[0], 3)]
