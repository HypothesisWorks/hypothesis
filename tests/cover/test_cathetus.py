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

import pytest

from hypothesis.internal.cathetus import cathetus


def assert_cathetus_exact(h, a, b):
    b0 = cathetus(h, a)
    assert b == b0, (
        'expected cathetus(%g, %g) == %g, got %g',
        h, a, b, b0
    )

def test_cathetus_negative():
    assert_cathetus_exact(-5, 4, 3)
    assert_cathetus_exact(5, -4, 3)
    assert_cathetus_exact(-5, -4, 3)

def test_cathetus_zero():
    assert_cathetus_exact(0, 0, 0)
    assert_cathetus_exact(1, 0, 1)

def test_pythagorean_triples():
    triples = [
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
        (68, 285, 293)
    ]
    for triple in triples:
        a, b, h = triple
        assert_cathetus_exact(h, a, b)
