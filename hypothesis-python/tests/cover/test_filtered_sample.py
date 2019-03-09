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
from hypothesis.strategies import filtered_sample


def test_cannot_sample_empty():
    with pytest.raises(InvalidArgument):
        filtered_sample([], lambda x: True).validate()


def test_can_find_rare_value():
    # An arbitrary number, high enough to fail if ordinary filtering is used.
    n = 100000
    target = n - 4
    x = filtered_sample(list(hrange(n)), lambda x: x == target).example()
    assert x == target


@given(
    data=st.data(),
    values=st.lists(st.integers(10, 20), min_size=1),
    threshold=st.integers(0, 30),
)
def test_agrees_with_values_and_condition(data, values, threshold):
    value = data.draw(filtered_sample(values, lambda x: x < threshold))
    assert value in values
    assert value < threshold
