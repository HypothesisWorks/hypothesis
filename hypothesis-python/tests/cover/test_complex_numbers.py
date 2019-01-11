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

import math
import sys

import hypothesis.strategies as st
from hypothesis import assume, given, reject
from hypothesis.strategies import complex_numbers
from tests.common.debug import minimal


def test_minimal():
    assert minimal(complex_numbers(), lambda x: True) == 0


def test_minimal_nonzero_real():
    assert minimal(complex_numbers(), lambda x: x.real != 0) == 1


def test_minimal_nonzero_imaginary():
    assert minimal(complex_numbers(), lambda x: x.imag != 0) == 1j


def test_minimal_quadrant1():
    assert minimal(complex_numbers(), lambda x: x.imag > 0 and x.real > 0) == 1 + 1j


def test_minimal_quadrant2():
    assert minimal(complex_numbers(), lambda x: x.imag > 0 and x.real < 0) == -1 + 1j


def test_minimal_quadrant3():
    assert minimal(complex_numbers(), lambda x: x.imag < 0 and x.real < 0) == -1 - 1j


def test_minimal_quadrant4():
    assert minimal(complex_numbers(), lambda x: x.imag < 0 and x.real > 0) == 1 - 1j


@given(st.data(), st.integers(-5, 5).map(lambda x: 10 ** x))
def test_max_magnitude_respected(data, mag):
    c = data.draw(complex_numbers(max_magnitude=mag))
    assert abs(c) <= mag * (1 + sys.float_info.epsilon)


@given(complex_numbers(max_magnitude=0))
def test_max_magnitude_zero(val):
    assert val == 0


@given(st.data(), st.integers(-5, 5).map(lambda x: 10 ** x))
def test_min_magnitude_respected(data, mag):
    c = data.draw(complex_numbers(min_magnitude=mag))
    assert (
        abs(c.real) >= mag
        or abs(c.imag) >= mag
        or abs(c) >= mag * (1 - sys.float_info.epsilon)
    )


def test_minimal_min_magnitude_zero():
    assert minimal(complex_numbers(min_magnitude=0), lambda x: True) == 0


def test_minimal_min_magnitude_none():
    assert minimal(complex_numbers(min_magnitude=None), lambda x: True) == 0


def test_minimal_min_magnitude_positive():
    assert minimal(complex_numbers(min_magnitude=0.5), lambda x: True) in (0.5, 1)


def test_minimal_minmax_magnitude():
    assert minimal(
        complex_numbers(min_magnitude=0.5, max_magnitude=1.5), lambda x: True
    ) in (0.5, 1)


@given(st.data(), st.floats(0, allow_infinity=False, allow_nan=False))
def test_minmax_magnitude_equal(data, mag):
    val = data.draw(st.complex_numbers(min_magnitude=mag, max_magnitude=mag))
    try:
        assume(abs(val) < float("inf"))
        assert math.isclose(abs(val), mag)
    except OverflowError:
        reject()
    except AttributeError:
        pass  # Python 2.7.3 does not have math.isclose
