# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import math

from pytest import raises

from flaky import flaky
from hypothesis import given, Settings
from hypothesis.internal import debug
from hypothesis.strategies import lists, floats


@flaky(max_runs=10, min_passes=1)
def test_can_timeout_during_an_unsuccessful_simplify():
    record = []

    @debug.timeout(3)
    @given(lists(floats()), settings=Settings(timeout=1))
    def first_bad_float_list(xs):
        if record:
            assert record[0] != xs
        elif len(xs) >= 10 and any(math.isinf(x) for x in xs):
            record.append(xs)
            assert False

    with raises(AssertionError):
        first_bad_float_list()
