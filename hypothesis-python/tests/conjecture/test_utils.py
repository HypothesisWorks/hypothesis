# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from fractions import Fraction

import pytest

from hypothesis import (
    HealthCheck,
    Phase,
    assume,
    example,
    given,
    settings,
    strategies as st,
)
from hypothesis.errors import InvalidArgument
from hypothesis.internal.conjecture import utils as cu
from hypothesis.internal.conjecture.data import ConjectureData, Status, StopTest
from hypothesis.internal.coverage import IN_COVERAGE_TESTS

try:
    import numpy as np
except ImportError:
    np = None


def test_drawing_certain_coin_still_writes():
    data = ConjectureData.for_choices([True])
    assert data.draw_boolean(1)
    assert data.choices == (True,)


def test_drawing_impossible_coin_still_writes():
    data = ConjectureData.for_choices([False])
    assert not data.draw_boolean(0)
    assert data.choices == (False,)


def test_draws_extremely_small_p():
    data = ConjectureData.for_choices((True,))
    assert data.draw_boolean(0.5**65)


@example([Fraction(1, 3), Fraction(1, 3), Fraction(1, 3)])
@example([Fraction(1, 1), Fraction(1, 2)])
@example([Fraction(1, 2), Fraction(4, 10)])
@example([Fraction(1, 1), Fraction(3, 5), Fraction(1, 1)])
@example([Fraction(2, 257), Fraction(2, 5), Fraction(1, 11)])
@example([0, 2, 47])
@settings(
    deadline=None,
    suppress_health_check=list(HealthCheck),
    phases=[Phase.explicit] if IN_COVERAGE_TESTS else settings.default.phases,
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
    assert sampler.sample(ConjectureData.for_choices([0, 0])) != 0


def test_sampler_shrinks():
    sampler = cu.Sampler([4.0, 8.0, 1.0, 1.0, 0.5])
    assert sampler.sample(ConjectureData.for_choices([0] * 3)) == 0


def test_can_force_sampler():
    sampler = cu.Sampler([0.5, 0.5])
    cd = ConjectureData.for_choices([0] * 100)
    assert sampler.sample(cd, forced=0) == 0
    assert sampler.sample(cd, forced=1) == 1


def test_combine_labels_is_distinct():
    x = 10
    y = 100
    assert cu.combine_labels(x, y) not in (x, y)


@given(st.integers())
def test_combine_labels_is_identity_for_single_argument(n):
    assert cu.combine_labels(n) == n


@pytest.mark.skipif(np is None, reason="requires Numpy")
def test_invalid_numpy_sample():
    with pytest.raises(InvalidArgument):
        cu.check_sample(np.array([[1, 1], [1, 1]]), "array")


@pytest.mark.skipif(np is None, reason="requires Numpy")
def test_valid_numpy_sample():
    cu.check_sample(np.array([1, 2, 3]), "array")


def test_invalid_set_sample():
    with pytest.raises(InvalidArgument):
        cu.check_sample({1, 2, 3}, "array")


def test_valid_list_sample():
    cu.check_sample([1, 2, 3], "array")


def test_choice():
    assert ConjectureData.for_choices([1]).choice([1, 2, 3]) == 2


def test_fixed_size_draw_many():
    many = cu.many(
        ConjectureData.for_choices([]), min_size=3, max_size=3, average_size=3
    )
    assert many.more()
    assert many.more()
    assert many.more()
    assert not many.more()


def test_astronomically_unlikely_draw_many():
    # Our internal helper doesn't underflow to zero or negative, but nor
    # will we ever generate an element for such a low average size.
    data = ConjectureData.for_choices((True,) * 1000)
    many = cu.many(data, min_size=0, max_size=10, average_size=1e-5)
    assert many.more()


def test_rejection_eventually_terminates_many():
    many = cu.many(
        ConjectureData.for_choices((True,) * 1000),
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
    data = ConjectureData.for_choices((True,) * 1000)
    many = cu.many(data, min_size=1, max_size=1000, average_size=100)

    with pytest.raises(StopTest):
        while many.more():
            many.reject()

    assert data.status == Status.INVALID


def test_many_with_min_size():
    many = cu.many(
        ConjectureData.for_choices((False,) * 5),
        min_size=2,
        average_size=10,
        max_size=1000,
    )
    assert many.more()
    assert many.more()
    assert not many.more()


def test_many_with_max_size():
    many = cu.many(
        ConjectureData.for_choices((True,) * 5), min_size=0, average_size=1, max_size=2
    )
    assert many.more()
    assert many.more()
    assert not many.more()


def test_samples_from_a_range_directly():
    s = cu.check_sample(range(10**1000), "")
    assert isinstance(s, range)


def test_p_continue_to_average_saturates():
    assert cu._p_continue_to_avg(1.1, 100) == 100
