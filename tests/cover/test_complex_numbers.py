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

from __future__ import division, print_function, absolute_import

import sys
import math

import pytest

from hypothesis import given
from tests.common.debug import minimal
from hypothesis.strategies import complex_numbers


def test_minimal_complex_number_is_zero():
    assert minimal(complex_numbers(), lambda x: True) == 0 + 0j


def test_can_minimal_standard_complex_numbers():
    assert minimal(complex_numbers(), lambda x: x.imag != 0) == 0 + 1j
    assert minimal(complex_numbers(), lambda x: x.real != 0) == 1 + 0j


@pytest.mark.parametrize('k', range(-5, 5))
def test_max_magnitude_respected(k):
    m = 10**k
    assert abs(
        minimal(complex_numbers(max_magnitude=m), lambda x: True)
    ) <= m
