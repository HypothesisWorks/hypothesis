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

import numpy as np
import pytest
from flaky import flaky

import hypothesis.strategies as st
from hypothesis import find, given, settings
from hypothesis.extra.numpy import arrays, from_dtype
from hypothesis.strategytests import strategy_test_suite
from hypothesis.internal.compat import text_type, binary_type

TestFloats = strategy_test_suite(arrays(float, ()))
TestIntMatrix = strategy_test_suite(arrays(int, (3, 2)))
TestBoolTensor = strategy_test_suite(arrays(bool, (2, 2, 2)))


STANDARD_TYPES = list(map(np.dtype, [
    u'int8', u'int32', u'int64',
    u'float', u'float32', u'float64',
    complex,
    bool, text_type, binary_type
]))


@pytest.mark.parametrize(u't', STANDARD_TYPES)
def test_produces_instances(t):
    @given(from_dtype(t))
    def test_is_t(x):
        assert isinstance(x, t.type)
        assert x.dtype.kind == t.kind
    test_is_t()


@given(arrays(float, ()))
def test_empty_dimensions_are_scalars(x):
    assert isinstance(x, np.dtype(float).type)


@given(arrays(u'uint32', (5, 5)))
def test_generates_unsigned_ints(x):
    assert (x >= 0).all()


@given(arrays(int, (1,)))
def test_assert_fits_in_machine_size(x):
    pass


def test_generates_and_minimizes():
    x = find(arrays(float, (2, 2)), lambda t: True)
    assert (x == np.zeros(shape=(2, 2), dtype=float)).all()


def test_can_minimize_large_arrays():
    x = find(arrays(u'uint32', 500), lambda t: t.any())
    assert x.sum() == 1


@flaky(max_runs=5, min_passes=1)
def test_can_minimize_float_arrays():
    x = find(
        arrays(float, 50), lambda t: t.sum() >= 1.0,
        settings=settings(database=None))
    assert 1.0 <= x.sum() <= 1.1


class Foo(object):
    pass


foos = st.tuples().map(lambda _: Foo())


def test_can_create_arrays_of_composite_types():
    arr = find(arrays(object, 100, foos), lambda x: True)
    for x in arr:
        assert isinstance(x, Foo)


def test_can_create_arrays_of_tuples():
    arr = find(
        arrays(object, 10, st.tuples(st.integers(), st.integers())),
        lambda x: all(t[0] != t[1] for t in x))
    for a in arr:
        assert a in ((1, 0), (0, 1))
