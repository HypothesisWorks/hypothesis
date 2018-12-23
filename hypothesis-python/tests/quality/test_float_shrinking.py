# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

from __future__ import absolute_import, division, print_function

from random import Random

import pytest

import hypothesis.strategies as st
from hypothesis import HealthCheck, Verbosity, assume, example, given, settings
from hypothesis.internal.compat import ceil, floor
from tests.common.debug import minimal


def test_shrinks_to_simple_floats():
    assert minimal(st.floats(), lambda x: x > 1) == 2.0
    assert minimal(st.floats(), lambda x: x > 0) == 1.0


@pytest.mark.parametrize("n", [1, 2, 3, 8, 10])
def test_can_shrink_in_variable_sized_context(n):
    x = minimal(st.lists(st.floats(), min_size=n), any)
    assert len(x) == n
    assert x.count(0.0) == n - 1
    assert 1 in x


@example(1.7976931348623157e308)
@example(1.5)
@given(st.floats(min_value=0, allow_infinity=False, allow_nan=False))
@settings(deadline=None, suppress_health_check=HealthCheck.all())
def test_shrinks_downwards_to_integers(f):
    g = minimal(
        st.floats(),
        lambda x: x >= f,
        random=Random(0),
        settings=settings(verbosity=Verbosity.quiet),
    )
    assert g == ceil(f)


@example(1)
@given(st.integers(1, 2 ** 16 - 1))
@settings(deadline=None, suppress_health_check=HealthCheck.all(), max_examples=10)
def test_shrinks_downwards_to_integers_when_fractional(b):
    g = minimal(
        st.floats(),
        lambda x: assume((0 < x < (2 ** 53)) and int(x) != x) and x >= b,
        random=Random(0),
        settings=settings(verbosity=Verbosity.quiet),
    )
    assert g == b + 0.5


@given(st.floats(min_value=0, allow_infinity=False))
@settings(deadline=None, suppress_health_check=HealthCheck.all())
def test_shrinks_integer_above_min_value(f):
    g = minimal(st.floats(min_value=f))
    assert g == ceil(f)


@given(st.floats(max_value=0, allow_infinity=False))
@settings(deadline=None, suppress_health_check=HealthCheck.all())
def test_shrinks_integer_below_max_value(f):
    g = minimal(st.floats(max_value=f))
    assert g == floor(f)
