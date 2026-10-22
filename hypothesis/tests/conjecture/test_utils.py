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

    for expected, actual in zip(probabilities, calculated, strict=True):
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


def count_many(*args, **kwargs):
    with cu.many(*args, **kwargs) as elements:
        return sum(1 for _ in elements)


def test_fixed_size_draw_many():
    data = ConjectureData.for_choices([])
    assert count_many(data, min_size=3, max_size=3, average_size=3) == 3


def test_astronomically_unlikely_draw_many():
    # Our internal helper doesn't underflow to zero or negative, but nor
    # will we ever generate an element for such a low average size.
    data = ConjectureData.for_choices((True,) * 1000)
    with cu.many(data, min_size=0, max_size=10, average_size=1e-5) as elements:
        assert next(iter(elements)) is None


def test_rejection_eventually_terminates_many():
    data = ConjectureData.for_choices((True,) * 1000)
    count = 0
    with cu.many(data, min_size=0, max_size=1000, average_size=100) as elements:
        for _ in elements:
            count += 1
            elements.reject()
    assert count <= 100


def test_rejection_eventually_terminates_many_invalid_for_min_size():
    data = ConjectureData.for_choices((True,) * 1000)
    with (
        pytest.raises(StopTest),
        cu.many(data, min_size=1, max_size=1000, average_size=100) as elements,
    ):
        for _ in elements:
            elements.reject()
    assert data.status == Status.INVALID


def many_span_discards(data):
    data.freeze()
    return [s.discarded for s in data.spans if s.label == cu.ONE_FROM_MANY_LABEL]


def test_rejected_element_span_is_discarded():
    data = ConjectureData.for_choices([True, 0, True, 1, False])
    with cu.many(data, min_size=0, max_size=10, average_size=5) as elements:
        for _ in elements:
            if data.draw_integer(0, 10) == 0:
                elements.reject()
    # the rejected first element is discarded; the second and the final
    # stop-drawing span are not.
    assert many_span_discards(data) == [True, False, False]


def test_many_with_min_size():
    data = ConjectureData.for_choices((False,) * 5)
    assert count_many(data, min_size=2, average_size=10, max_size=1000) == 2


def test_many_with_max_size():
    data = ConjectureData.for_choices((True,) * 5)
    assert count_many(data, min_size=0, average_size=1, max_size=2) == 2


@pytest.mark.parametrize("reject", [False, True])
def test_break_from_many_draws_forced_stop(reject):
    data = ConjectureData.for_choices([True, 0, True, 1, True, 2, False])
    depth = data.depth
    with cu.many(data, min_size=0, max_size=10, average_size=5) as elements:
        for _ in elements:
            if data.draw_integer(0, 10) == 1:
                if reject:
                    elements.reject()
                break
    assert data.depth == depth
    assert data.choices == (True, 0, True, 1, False)
    assert data.nodes[-1].was_forced
    assert many_span_discards(data) == [False, reject, False]


def test_exception_in_many_closes_spans():
    data = ConjectureData.for_choices([True, 0, True, 1, False])
    depth = data.depth
    with (
        pytest.raises(ZeroDivisionError),
        cu.many(data, min_size=0, max_size=10, average_size=5) as elements,
    ):
        for _ in elements:
            data.draw_integer(0, 10)
            1 / 0
    assert data.depth == depth
    assert data.choices == (True, 0)


def test_break_from_many_below_min_size_is_invalid():
    data = ConjectureData.for_choices([True, 0, True, 1, False])
    with (
        pytest.raises(StopTest),
        cu.many(data, min_size=2, max_size=10, average_size=5) as elements,
    ):
        for _ in elements:
            break
    assert data.status == Status.INVALID


def new_many(data=None):
    data = data or ConjectureData.for_choices((True,) * 10 + (False,))
    return cu.many(data, min_size=0, max_size=10, average_size=5)


def test_many_must_be_used_as_context_manager():
    with pytest.raises(InvalidArgument):
        for _ in new_many():
            pass


def test_many_cannot_be_iterated_after_exit():
    with new_many() as elements:
        pass
    with pytest.raises(InvalidArgument):
        for _ in elements:
            pass


def test_many_cannot_resume_iteration_after_exit():
    with new_many() as elements:
        it = iter(elements)
        next(it)
    with pytest.raises(InvalidArgument):
        next(it)


def test_many_detects_unbalanced_spans_on_exit():
    data = ConjectureData.for_choices((True,) * 10 + (False,))
    with pytest.raises(InvalidArgument, match="interleaved"), new_many(data):
        data.start_span(1)


def test_many_cannot_be_iterated_twice():
    with new_many() as elements:
        for _ in elements:
            break
        with pytest.raises(InvalidArgument):
            for _ in elements:
                pass


def test_many_cannot_be_entered_twice():
    m = new_many()
    with m:
        pass
    with pytest.raises(InvalidArgument), m:
        pass


def test_many_detects_interleaved_iteration():
    data = ConjectureData.for_choices((True,) * 10 + (False,))
    with (
        pytest.raises(InvalidArgument, match="interleaved"),
        new_many(data) as a,
        new_many(data) as b,
    ):
        for _ in zip(a, b, strict=True):
            pass


@pytest.mark.parametrize("when", ["before", "twice", "after"])
def test_many_reject_outside_element_is_an_error(when):
    with pytest.raises(InvalidArgument), new_many() as elements:
        if when == "before":
            elements.reject()
        for _ in elements:
            if when == "twice":
                elements.reject()
                elements.reject()
        elements.reject()


def test_invert_many_variable_size():
    many = cu.invert_many(min_size=0, max_size=5)
    assert many.more() == (True,)
    assert many.done() == (False,)


def test_invert_many_fixed_size():
    many = cu.invert_many(min_size=3, max_size=3)
    assert many.more() == ()
    assert many.done() == ()


def test_samples_from_a_range_directly():
    s = cu.check_sample(range(10**1000), "")
    assert isinstance(s, range)


def test_p_continue_to_average_saturates():
    assert cu._p_continue_to_avg(1.1, 100) == 100


def test_unhashable_calc_label():

    class Unhashable:
        def __call__(self):
            return None

        def __hash__(self):
            raise TypeError

    c1 = Unhashable()
    c2 = Unhashable()

    with pytest.raises(TypeError):
        assert cu.calc_label_from_hash(c1) == cu.calc_label_from_hash(c2)
    assert cu.calc_label_from_callable(c1) == cu.calc_label_from_callable(c2)
