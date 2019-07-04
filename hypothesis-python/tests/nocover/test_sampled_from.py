# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import pytest

import hypothesis.strategies as st
from hypothesis import given
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import hrange
from tests.common.utils import counts_calls, fails_with


@pytest.mark.parametrize("n", [100, 10 ** 5, 10 ** 6, 2 ** 25])
def test_filter_large_lists(n):
    filter_limit = 100 * 10000

    @counts_calls
    def cond(x):
        assert cond.calls < filter_limit
        return x % 2 != 0

    s = st.sampled_from(hrange(n)).filter(cond)

    @given(s)
    def run(x):
        assert x % 2 != 0

    run()

    assert cond.calls < filter_limit


def rare_value_strategy(n, target):
    def forbid(s, forbidden):
        """Helper function to avoid Python variable scoping issues."""
        return s.filter(lambda x: x != forbidden)

    s = st.sampled_from(hrange(n))
    for i in hrange(n):
        if i != target:
            s = forbid(s, i)

    return s


@given(rare_value_strategy(n=128, target=80))
def test_chained_filters_find_rare_value(x):
    assert x == 80


@fails_with(InvalidArgument)
@given(st.sets(st.sampled_from(range(10)), min_size=11))
def test_unsat_sets_of_samples(x):
    assert False


@given(st.sets(st.sampled_from(range(50)), min_size=50))
def test_efficient_sets_of_samples(x):
    assert x == set(range(50))
