# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import time

from pytest import raises

from hypothesis import given, settings
from hypothesis.internal import debug
from hypothesis.strategies import lists, integers


def test_can_timeout_during_an_unsuccessful_simplify():
    record = []

    @debug.timeout(3)
    @given(lists(integers(), min_size=10))
    @settings(timeout=1, database=None)
    def first_bad_float_list(xs):
        if record:
            time.sleep(0.1)
            assert record[0] != xs
        elif sum(xs) >= 10 ** 6:
            record.append(xs)
            assert False

    with raises(AssertionError):
        first_bad_float_list()
