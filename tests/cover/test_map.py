# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/HypothesisWorks/hypothesis-python)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/HypothesisWorks/hypothesis-python/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import pytest

from hypothesis import strategies as st
from hypothesis import given, assume
from hypothesis.errors import NoExamples


@given(st.integers().map(lambda x: assume(x % 3 != 0) and x))
def test_can_assume_in_map(x):
    assert x % 3 != 0


def test_assume_in_just_raises_immediately():
    with pytest.raises(NoExamples):
        st.just(1).map(lambda x: assume(x == 2)).example()
