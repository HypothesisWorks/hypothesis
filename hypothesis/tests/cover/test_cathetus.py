# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math
import sys
from sys import float_info

import pytest

from hypothesis import assume, given
from hypothesis.internal.cathetus import cathetus
from hypothesis.strategies import floats


def test_cathetus_subnormal_underflow():
    u = sys.float_info.min * sys.float_info.epsilon
    h = 5 * u
    a = 4 * u
    assert cathetus(h, a) == 3 * u


def test_cathetus_simple_underflow():
    a = sys.float_info.min
    h = a * math.sqrt(2)
    b = cathetus(h, a)
    assert b > 0, f"expecting positive cathetus({h:g}, {a:g}), got {b:g}"


def test_cathetus_huge_no_overflow():
    h = sys.float_info.max
    a = h / math.sqrt(2)
    b = cathetus(h, a)
    assert math.isfinite(b), f"expecting finite cathetus({h:g}, {a:g}), got {b:g}"


def test_cathetus_large_no_overflow():
    h = sys.float_info.max / 3
    a = h / math.sqrt(2)
    b = cathetus(h, a)
    assert math.isfinite(b), f"expecting finite cathetus({h:g}, {a:g}), got {b:g}"


@pytest.mark.parametrize(
    "h,a",
    [
        # NaN hypot
        (math.nan, 3),
        (math.nan, 0),
        (math.nan, math.inf),
        (math.nan, math.nan),
        # Infeasible
        (2, 3),
        (2, -3),
        (2, math.inf),
        (2, math.nan),
        # Surprisingly consistent with c99 hypot()
        (math.inf, math.inf),
    ],
)
def test_cathetus_nan(h, a):
    assert math.isnan(cathetus(h, a))


@pytest.mark.parametrize(
    "h,a", [(math.inf, 3), (math.inf, -3), (math.inf, 0), (math.inf, math.nan)]
)
def test_cathetus_infinite(h, a):
    assert math.isinf(cathetus(h, a))


@pytest.mark.parametrize(
    "h,a,b", [(-5, 4, 3), (5, -4, 3), (-5, -4, 3), (0, 0, 0), (1, 0, 1)]
)
def test_cathetus_signs(h, a, b):
    assert abs(cathetus(h, a) - b) <= abs(b) * float_info.epsilon


@given(
    h=floats(0) | floats(min_value=1e308, allow_infinity=False),
    a=floats(0, allow_infinity=False)
    | floats(min_value=0, max_value=1e250, allow_infinity=False),
)
def test_cathetus_always_leq_hypot(h, a):
    assume(h >= a)
    b = cathetus(h, a)
    assert 0 <= b <= h


@pytest.mark.parametrize(
    "a,b,h",
    [
        (3, 4, 5),
        (5, 12, 13),
        (8, 15, 17),
        (7, 24, 25),
        (20, 21, 29),
        (12, 35, 37),
        (9, 40, 41),
        (28, 45, 53),
        (11, 60, 61),
        (16, 63, 65),
        (33, 56, 65),
        (48, 55, 73),
        (13, 84, 85),
        (36, 77, 85),
        (39, 80, 89),
        (65, 72, 97),
        (20, 99, 101),
        (60, 91, 109),
        (15, 112, 113),
        (44, 117, 125),
        (88, 105, 137),
        (17, 144, 145),
        (24, 143, 145),
        (51, 140, 149),
        (85, 132, 157),
        (119, 120, 169),
        (52, 165, 173),
        (19, 180, 181),
        (57, 176, 185),
        (104, 153, 185),
        (95, 168, 193),
        (28, 195, 197),
        (84, 187, 205),
        (133, 156, 205),
        (21, 220, 221),
        (140, 171, 221),
        (60, 221, 229),
        (105, 208, 233),
        (120, 209, 241),
        (32, 255, 257),
        (23, 264, 265),
        (96, 247, 265),
        (69, 260, 269),
        (115, 252, 277),
        (160, 231, 281),
        (161, 240, 289),
        (68, 285, 293),
    ],
)
def test_pythagorean_triples(a, b, h):
    assert abs(math.hypot(a, b) - h) <= abs(h) * float_info.epsilon
    assert abs(cathetus(h, a) - b) <= abs(b) * float_info.epsilon
