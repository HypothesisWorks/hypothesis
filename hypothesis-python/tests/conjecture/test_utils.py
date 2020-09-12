# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

from collections import Counter
from fractions import Fraction

import numpy as np
import pytest

from hypothesis import (
    HealthCheck,
    Phase,
    assume,
    example,
    given,
    reject,
    settings,
    strategies as st,
)
from hypothesis.errors import InvalidArgument
from hypothesis.internal.conjecture import utils as cu
from hypothesis.internal.conjecture.data import ConjectureData, Status, StopTest
from hypothesis.internal.coverage import IN_COVERAGE_TESTS


def test_does_draw_data_for_empty_range():
    data = ConjectureData.for_buffer(b"\1")
    assert cu.integer_range(data, 1, 1) == 1
    data.freeze()
    assert data.buffer == b"\0"


def test_uniform_float_shrinks_to_zero():
    d = ConjectureData.for_buffer(bytes(7))
    assert cu.fractional_float(d) == 0.0
    assert len(d.buffer) == 7


def test_uniform_float_can_draw_1():
    d = ConjectureData.for_buffer(bytes([255] * 7))
    assert cu.fractional_float(d) == 1.0
    assert len(d.buffer) == 7


def test_coin_biased_towards_truth():
    p = 1 - 1.0 / 500

    for i in range(1, 255):
        assert cu.biased_coin(ConjectureData.for_buffer([0, i, 0, 0]), p)

    assert not cu.biased_coin(ConjectureData.for_buffer([0, 0, 0, 1]), p)


def test_coin_biased_towards_falsehood():
    p = 1.0 / 500

    for i in range(255):
        if i != 1:
            assert not cu.biased_coin(ConjectureData.for_buffer([0, i, 0, 1]), p)
    assert cu.biased_coin(ConjectureData.for_buffer([0, 1, 0, 0]), p)


def test_unbiased_coin_has_no_second_order():
    counts = Counter()

    for i in range(256):
        buf = bytes([i])
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
    total = 0
    p = Fraction(3, 8)
    for i in range(4):
        for j in range(4):
            total += 1
            if cu.biased_coin(ConjectureData.for_buffer([i, j, 0]), p):
                count += 1
    assert p == Fraction(count, total)


def test_too_small_to_be_useful_coin():
    assert not cu.biased_coin(ConjectureData.for_buffer([1]), 0.5 ** 65)


@example([Fraction(1, 3), Fraction(1, 3), Fraction(1, 3)])
@example([Fraction(1, 1), Fraction(1, 2)])
@example([Fraction(1, 2), Fraction(4, 10)])
@example([Fraction(1, 1), Fraction(3, 5), Fraction(1, 1)])
@example([Fraction(2, 257), Fraction(2, 5), Fraction(1, 11)])
@example([0, 2, 47])
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

    for expected, actual in zip(probabilities, calculated):
        if isinstance(actual, Fraction):
            assert expected == actual
        else:
            assert abs(expected - actual) < 0.001


def test_sampler_does_not_draw_minimum_if_zero():
    sampler = cu.Sampler([0, 2, 47])
    assert sampler.sample(ConjectureData.for_buffer([0, 0])) != 0


def test_integer_range_center_upper():
    assert (
        cu.integer_range(ConjectureData.for_buffer([0]), lower=0, upper=10, center=10)
        == 10
    )


def test_integer_range_center_lower():
    assert (
        cu.integer_range(ConjectureData.for_buffer([0]), lower=0, upper=10, center=0)
        == 0
    )


def test_integer_range_lower_equals_upper():
    data = ConjectureData.for_buffer([0])

    assert cu.integer_range(data, lower=0, upper=0, center=0) == 0

    assert len(data.buffer) == 1


def test_integer_range_center_default():
    assert (
        cu.integer_range(ConjectureData.for_buffer([0]), lower=0, upper=10, center=None)
        == 0
    )


def test_center_in_middle_below():
    assert (
        cu.integer_range(ConjectureData.for_buffer([0, 0]), lower=0, upper=10, center=5)
        == 5
    )


def test_center_in_middle_above():
    assert (
        cu.integer_range(ConjectureData.for_buffer([1, 0]), lower=0, upper=10, center=5)
        == 5
    )


def test_restricted_bits():
    assert (
        cu.integer_range(
            ConjectureData.for_buffer([1, 0, 0, 0, 0]), lower=0, upper=2 ** 64 - 1
        )
        == 0
    )


def test_sampler_shrinks():
    sampler = cu.Sampler([4.0, 8.0, 1.0, 1.0, 0.5])
    assert sampler.sample(ConjectureData.for_buffer([0] * 3)) == 0


def test_combine_labels_is_distinct():
    x = 10
    y = 100
    assert cu.combine_labels(x, y) not in (x, y)


def test_invalid_numpy_sample():
    with pytest.raises(InvalidArgument):
        cu.check_sample(np.array([[1, 1], [1, 1]]), "array")


def test_valid_numpy_sample():
    cu.check_sample(np.array([1, 2, 3]), "array")


def test_invalid_set_sample():
    with pytest.raises(InvalidArgument):
        cu.check_sample({1, 2, 3}, "array")


def test_valid_list_sample():
    cu.check_sample([1, 2, 3], "array")


def test_choice():
    assert cu.choice(ConjectureData.for_buffer([1]), [1, 2, 3]) == 2


def test_fractional_float():
    assert cu.fractional_float(ConjectureData.for_buffer([0] * 8)) == 0.0


def test_fixed_size_draw_many():
    many = cu.many(
        ConjectureData.for_buffer([]), min_size=3, max_size=3, average_size=3
    )
    assert many.more()
    assert many.more()
    assert many.more()
    assert not many.more()


def test_rejection_eventually_terminates_many():
    many = cu.many(
        ConjectureData.for_buffer([1] * 1000),
        min_size=0,
        max_size=1000,
        average_size=100,
    )
    count = 0

    while many.more():
        count += 1
        many.reject()

    assert count <= 100


def test_rejection_eventually_terminates_many_invalid_for_min_size():
    data = ConjectureData.for_buffer([1] * 1000)
    many = cu.many(data, min_size=1, max_size=1000, average_size=100)

    with pytest.raises(StopTest):
        while many.more():
            many.reject()

    assert data.status == Status.INVALID


def test_many_with_min_size():
    many = cu.many(
        ConjectureData.for_buffer([0] * 10), min_size=2, average_size=10, max_size=1000
    )
    assert many.more()
    assert many.more()
    assert not many.more()


def test_many_with_max_size():
    many = cu.many(
        ConjectureData.for_buffer([1] * 10), min_size=0, average_size=1, max_size=2
    )
    assert many.more()
    assert many.more()
    assert not many.more()


def test_biased_coin_can_be_forced():
    assert cu.biased_coin(ConjectureData.for_buffer([0]), p=0.5, forced=True)
    assert not cu.biased_coin(ConjectureData.for_buffer([1]), p=0.5, forced=False)


def test_assert_biased_coin_always_treats_one_as_true():
    assert cu.biased_coin(ConjectureData.for_buffer([0, 1]), p=1.0 / 257)


@example(p=0.31250000000000006, b=b"\x03\x03\x00")
@example(p=0.4375000000000001, b=b"\x03\x00")
@given(st.floats(0, 1), st.binary())
def test_can_draw_arbitrary_fractions(p, b):
    try:
        cu.biased_coin(ConjectureData.for_buffer(b), p)
    except StopTest:
        reject()


def test_samples_from_a_range_directly():
    s = cu.check_sample(range(10 ** 1000), "")
    assert isinstance(s, range)
