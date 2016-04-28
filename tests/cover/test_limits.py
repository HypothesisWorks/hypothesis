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

from hypothesis import strategies as st
from hypothesis import given, settings


def test_max_examples_are_respected():
    counter = [0]

    @given(st.random_module(), st.integers())
    @settings(max_examples=100)
    def test(rnd, i):
        counter[0] += 1
    test()
    assert counter == [100]
