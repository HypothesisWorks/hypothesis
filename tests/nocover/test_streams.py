# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

from itertools import islice

from hypothesis import given, assume
from hypothesis.strategies import integers, streaming
from hypothesis.internal.compat import integer_types


@given(streaming(integers()))
def test_can_adaptively_assume_about_streams(xs):
    for i in islice(xs, 200):
        assume(i >= 0)


@given(streaming(integers()))
def test_streams_are_arbitrarily_long(ss):
    for i in islice(ss, 100):
        assert isinstance(i, integer_types)
