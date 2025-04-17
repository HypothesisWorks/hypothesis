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

import pytest

import hypothesis.strategies as st
from hypothesis import HealthCheck, example, given, settings
from hypothesis.internal.conjecture import utils as cu
from hypothesis.internal.conjecture.choice import choice_equal
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.floats import SIGNALING_NAN, SMALLEST_SUBNORMAL

from tests.conjecture.common import choice_types_constraints, fresh_data


@given(st.data())
@settings(
    database=None,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
)
def test_forced_many(data):
    forced = data.draw(st.integers(0, 100))
    min_size = data.draw(st.integers(0, forced))
    max_size = data.draw(st.integers(forced, 100))
    assert min_size <= forced <= max_size  # by construction

    data = fresh_data()
    many = cu.many(
        data,
        min_size=min_size,
        average_size=(min_size + max_size) / 2,
        max_size=max_size,
        forced=forced,
    )
    for _ in range(forced):
        assert many.more()

    assert not many.more()

    # ensure values written to the buffer do in fact generate the forced value
    data = ConjectureData.for_choices(data.choices)
    many = cu.many(
        data,
        min_size=min_size,
        average_size=(min_size + max_size) / 2,
        max_size=max_size,
    )
    for _ in range(forced):
        assert many.more()

    assert not many.more()


@example(("boolean", {"p": 1e-19, "forced": True}))  # 64 bit p
@example(("boolean", {"p": 3e-19, "forced": True}))  # 62 bit p
@example(
    (
        "integer",
        {
            "min_value": -1,
            "max_value": 1,
            "shrink_towards": 1,
            "weights": {-1: 0.2, 0: 0.2, 1: 0.2},
            "forced": 0,
        },
    )
)
@example(
    (
        "integer",
        {
            "min_value": -1,
            "max_value": 1,
            "shrink_towards": -1,
            "weights": {-1: 0.2, 0: 0.2, 1: 0.2},
            "forced": 0,
        },
    )
)
@example(
    (
        "integer",
        {
            "min_value": 10,
            "max_value": 1_000,
            "shrink_towards": 17,
            "weights": {20: 0.1},
            "forced": 15,
        },
    )
)
@example(
    (
        "integer",
        {
            "min_value": -1_000,
            "max_value": -10,
            "shrink_towards": -17,
            "weights": {-20: 0.1},
            "forced": -15,
        },
    )
)
@example(("float", {"forced": 0.0}))
@example(("float", {"forced": -0.0}))
@example(("float", {"forced": 1.0}))
@example(("float", {"forced": 1.2345}))
@example(("float", {"forced": SMALLEST_SUBNORMAL}))
@example(("float", {"forced": -SMALLEST_SUBNORMAL}))
@example(("float", {"forced": 100 * SMALLEST_SUBNORMAL}))
@example(("float", {"forced": math.nan}))
@example(("float", {"forced": -math.nan}))
@example(("float", {"forced": SIGNALING_NAN}))
@example(("float", {"forced": -SIGNALING_NAN}))
@example(("float", {"forced": 1e999}))
@example(("float", {"forced": -1e999}))
# previously errored on our {pos, neg}_clamper logic not considering nans.
@example(
    (
        "float",
        {"min_value": -1 * math.inf, "max_value": -1 * math.inf, "forced": math.nan},
    )
)
@given(choice_types_constraints(use_forced=True))
def test_forced_values(choice_type_and_constraints):
    (choice_type, constraints) = choice_type_and_constraints
    forced = constraints["forced"]
    data = fresh_data()
    assert choice_equal(getattr(data, f"draw_{choice_type}")(**constraints), forced)

    # now make sure the written buffer reproduces the forced value, even without
    # specifying forced=.
    del constraints["forced"]
    data = ConjectureData.for_choices(data.choices)
    assert choice_equal(getattr(data, f"draw_{choice_type}")(**constraints), forced)


@pytest.mark.parametrize("sign", [1, -1])
@pytest.mark.parametrize(
    "min_value, max_value",
    [
        (0.0, 0.0),
        (-0.0, -0.0),
        (0.0, 100.0),
        (-100.0, -0.0),
        (5.0, 10.0),
        (-10.0, -5.0),
    ],
)
@given(random=st.randoms())
def test_forced_floats_with_nan(random, sign, min_value, max_value):
    # nans with a sign opposite of both bounds previously gave us trouble
    # trying to use float clampers that didn't exist when drawing.
    data = fresh_data(random=random)
    data.draw_float(min_value=min_value, max_value=max_value, forced=sign * math.nan)


@given(st.data())
def test_forced_with_large_magnitude_integers(data):
    bound_offset = data.draw(st.integers(min_value=0))
    # forced_offset = bound_offset + st.integers(min_value=0) may look cleaner, but
    # has subtly different maximum value semantics as it is twice the range of a
    # single draw
    forced_offset = data.draw(st.integers(min_value=bound_offset))

    half_range = 2**127 + 1
    cd = fresh_data()
    cd.draw_integer(
        min_value=half_range + bound_offset, forced=half_range + forced_offset
    )

    cd = fresh_data()
    cd.draw_integer(
        max_value=-(half_range + bound_offset), forced=-(half_range + forced_offset)
    )
