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

from random import Random

import hypothesis.strategies as st
from hypothesis import given


@given(st.integers())
def test_deterministic_examples_are_deterministic(seed):
    assert st.lists(st.integers()).example(Random(seed)) == \
        st.lists(st.integers()).example(Random(seed))


def test_does_not_always_give_the_same_example():
    s = st.integers()
    assert len(set(
        s.example() for _ in range(100)
    )) >= 10
