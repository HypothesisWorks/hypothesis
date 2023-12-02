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
from random import Random

import pytest

import hypothesis.strategies as st
from hypothesis import HealthCheck, assume, given, settings
from hypothesis.internal.conjecture import utils as cu
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.strategies._internal.lazy import unwrap_strategies


# we'd like to use st.data() here, but that tracks too much global state for us
# to ensure its buffer was only written to by our forced draws.
def fresh_data():
    return ConjectureData(8 * 1024, prefix=b"", random=Random())


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
    data = ConjectureData.for_buffer(data.buffer)
    many = cu.many(
        data,
        min_size=min_size,
        average_size=(min_size + max_size) / 2,
        max_size=max_size,
    )
    for _ in range(forced):
        assert many.more()

    assert not many.more()


def test_forced_boolean():
    data = ConjectureData.for_buffer([0])
    assert data.draw_boolean(0.5, forced=True)

    data = ConjectureData.for_buffer([1])
    assert not data.draw_boolean(0.5, forced=False)


@pytest.mark.parametrize(
    "use_min_value, use_max_value, use_shrink_towards, use_weights",
    [
        (True, True, True, True),
        (True, True, True, False),
        (True, True, False, True),
        (True, True, False, False),
        (True, False, True, False),
        (False, True, True, False),
        (False, False, True, False),
        (False, True, False, False),
        (True, False, False, False),
        (False, False, False, False),
    ],
)
@given(st.data())
@settings(database=None)
def test_forced_integer(
    use_min_value, use_max_value, use_shrink_towards, use_weights, data
):
    min_value = None
    max_value = None
    shrink_towards = 0
    weights = None

    forced = data.draw(st.integers())
    if use_min_value:
        min_value = data.draw(st.integers(max_value=forced))
    if use_max_value:
        max_value = data.draw(st.integers(min_value=forced))
    if use_shrink_towards:
        shrink_towards = data.draw(st.integers())
    if use_weights:
        assert use_max_value
        assert use_min_value

        width = max_value - min_value + 1
        assume(width <= 1024)
        assume((forced - shrink_towards).bit_length() < 128)

        weights = data.draw(
            st.lists(
                # weights doesn't play well with super small floats.
                st.floats(min_value=0.1, max_value=1),
                min_size=width,
                max_size=width,
            )
        )

    data = fresh_data()
    assert (
        data.draw_integer(
            min_value,
            max_value,
            shrink_towards=shrink_towards,
            weights=weights,
            forced=forced,
        )
        == forced
    )

    data = ConjectureData.for_buffer(data.buffer)
    assert (
        data.draw_integer(
            min_value, max_value, shrink_towards=shrink_towards, weights=weights
        )
        == forced
    )


@pytest.mark.parametrize("use_min_size", [True, False])
@pytest.mark.parametrize("use_max_size", [True, False])
@given(st.data())
@settings(
    database=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_forced_string(use_min_size, use_max_size, data):
    forced_s = st.text()
    intervals = unwrap_strategies(forced_s).element_strategy.intervals

    forced = data.draw(forced_s)
    min_size = 0
    max_size = None
    if use_min_size:
        min_size = data.draw(st.integers(0, len(forced)))

    if use_max_size:
        max_size = data.draw(st.integers(min_value=len(forced)))

    data = fresh_data()
    assert (
        data.draw_string(
            intervals=intervals, min_size=min_size, max_size=max_size, forced=forced
        )
        == forced
    )

    data = ConjectureData.for_buffer(data.buffer)
    assert (
        data.draw_string(intervals=intervals, min_size=min_size, max_size=max_size)
        == forced
    )


@given(st.binary())
@settings(database=None)
def test_forced_bytes(forced):
    data = fresh_data()
    assert data.draw_bytes(len(forced), forced=forced) == forced

    data = ConjectureData.for_buffer(data.buffer)
    assert data.draw_bytes(len(forced)) == forced


@given(st.floats())
@settings(database=None)
def test_forced_floats(forced):
    data = fresh_data()
    drawn = data.draw_float(forced=forced)
    assert drawn == forced or (math.isnan(drawn) and math.isnan(forced))

    data = ConjectureData.for_buffer(data.buffer)
    drawn = data.draw_float()
    assert drawn == forced or (math.isnan(drawn) and math.isnan(forced))
