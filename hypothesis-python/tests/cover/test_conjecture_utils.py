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

from collections import Counter
from fractions import Fraction

import hypothesis.internal.conjecture.utils as cu
import hypothesis.strategies as st
from hypothesis import HealthCheck, Phase, assume, example, given, settings
from hypothesis.internal.compat import hbytes, hrange
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.coverage import IN_COVERAGE_TESTS


def test_does_draw_data_for_empty_range():
    data = ConjectureData.for_buffer(b"\1")
    assert cu.integer_range(data, 1, 1) == 1
    data.freeze()
    assert data.buffer == hbytes(b"\0")


def test_uniform_float_shrinks_to_zero():
    d = ConjectureData.for_buffer(hbytes([0] * 7))
    assert cu.fractional_float(d) == 0.0
    assert len(d.buffer) == 7


def test_uniform_float_can_draw_1():
    d = ConjectureData.for_buffer(hbytes([255] * 7))
    assert cu.fractional_float(d) == 1.0
    assert len(d.buffer) == 7


def test_coin_biased_towards_truth():
    p = 1 - 1.0 / 500

    for i in range(255):
        assert cu.biased_coin(ConjectureData.for_buffer([i]), p)

    second_order = [
        cu.biased_coin(ConjectureData.for_buffer([255, i]), p) for i in range(255)
    ]

    assert False in second_order
    assert True in second_order


def test_coin_biased_towards_falsehood():
    p = 1.0 / 500

    for i in range(255):
        assert not cu.biased_coin(ConjectureData.for_buffer([i]), p)

    second_order = [
        cu.biased_coin(ConjectureData.for_buffer([255, i]), p) for i in range(255)
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


def test_drawing_an_exact_fraction_coin():
    count = 0
    for i in hrange(8):
        if cu.biased_coin(ConjectureData.for_buffer([i]), Fraction(3, 8)):
            count += 1
    assert count == 3


@example([Fraction(1, 3), Fraction(1, 3), Fraction(1, 3)])
@example([Fraction(1, 1), Fraction(1, 2)])
@example([Fraction(1, 2), Fraction(4, 10)])
@example([Fraction(1, 1), Fraction(3, 5), Fraction(1, 1)])
@example([Fraction(2, 257), Fraction(2, 5), Fraction(1, 11)])
@settings(
    deadline=None,
    suppress_health_check=HealthCheck.all(),
    phases=[Phase.explicit] if IN_COVERAGE_TESTS else tuple(Phase),
)
@given(st.lists(st.fractions(min_value=0, max_value=1), min_size=1))
def test_sampler_distribution(weights):
    total = sum(weights)
    n = len(weights)

    assume(total > 0)

    probabilities = [w / total for w in weights]

    sampler = cu.Sampler(weights)

    calculated = [Fraction(0)] * n
    for base, alternate, p_alternate in sampler.table:
        calculated[base] += (1 - p_alternate) / n
        calculated[alternate] += p_alternate / n
    assert probabilities == calculated
