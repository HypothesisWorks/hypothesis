# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

from collections import Counter

import hypothesis.internal.conjecture.utils as cu
from hypothesis.internal.compat import hbytes
from hypothesis.internal.conjecture.data import ConjectureData


def test_does_not_draw_data_for_empty_range():
    assert cu.integer_range(ConjectureData.for_buffer(b''), 1, 1) == 1


def test_uniform_float_shrinks_to_zero():
    d = ConjectureData.for_buffer(hbytes([0] * 7))
    assert cu.fractional_float(d) == 0.0
    assert len(d.buffer) == 7


def test_uniform_float_can_draw_1():
    d = ConjectureData.for_buffer(hbytes([255] * 7))
    assert cu.fractional_float(d) == 1.0
    assert len(d.buffer) == 7


def test_geometric_can_handle_bad_first_draw():
    assert cu.geometric(ConjectureData.for_buffer(hbytes(
        [255] * 7 + [0] * 7)), 0.5) == 0


def test_coin_biased_towards_truth():
    p = 1 - 1.0 / 500

    for i in range(255):
        assert cu.biased_coin(
            ConjectureData.for_buffer([i]), p
        )

    second_order = [
        cu.biased_coin(ConjectureData.for_buffer([255, i]), p)
        for i in range(255)
    ]

    assert False in second_order
    assert True in second_order


def test_coin_biased_towards_falsehood():
    p = 1.0 / 500

    for i in range(255):
        assert not cu.biased_coin(
            ConjectureData.for_buffer([i]), p
        )

    second_order = [
        cu.biased_coin(ConjectureData.for_buffer([255, i]), p)
        for i in range(255)
    ]

    assert False in second_order
    assert True in second_order


def test_unbiased_coin_has_no_second_order():
    counts = Counter()

    for i in range(256):
        buf = hbytes([i])
        data = ConjectureData.for_buffer(buf)
        result = cu.biased_coin(data, 0.5)
        if data.buffer == buf:
            counts[result] += 1

    assert counts[False] == counts[True] > 0


def test_can_get_odd_number_of_bits():
    counts = Counter()
    for i in range(256):
        x = cu.getrandbits(ConjectureData.for_buffer([i]), 3)
        assert 0 <= x <= 7
        counts[x] += 1
    assert len(set(counts.values())) == 1


def test_8_bits_just_reads_stream():
    for i in range(256):
        assert cu.getrandbits(ConjectureData.for_buffer([i]), 8) == i


def test_drawing_certain_coin_still_writes():
    data = ConjectureData.for_buffer([0, 1])
    assert not data.buffer
    assert cu.biased_coin(data, 1)
    assert data.buffer


def test_drawing_impossible_coin_still_writes():
    data = ConjectureData.for_buffer([1, 0])
    assert not data.buffer
    assert not cu.biased_coin(data, 0)
    assert data.buffer
