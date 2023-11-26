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


@settings(
    database=None,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
)
@given(st.integers(0, 100), st.integers(0, 100), st.integers(0, 100))
def test_forced_many(min_size, max_size, forced):
    assume(min_size <= forced <= max_size)

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
    "min_value_s, max_value_s, shrink_towards_s, forced_s",
    [
        (st.integers(), st.integers(), st.integers(), st.integers()),
        (st.integers(), st.integers(), st.none(), st.integers()),
        (st.integers(), st.none(), st.integers(), st.integers()),
        (st.none(), st.integers(), st.integers(), st.integers()),
        (st.none(), st.none(), st.integers(), st.integers()),
        (st.none(), st.integers(), st.none(), st.integers()),
        (st.integers(), st.none(), st.none(), st.integers()),
        (st.none(), st.none(), st.none(), st.integers()),
    ],
)
def test_forced_integer(min_value_s, max_value_s, shrink_towards_s, forced_s):
    @given(min_value_s, max_value_s, shrink_towards_s, forced_s)
    @settings(database=None)
    def inner_test(min_value, max_value, shrink_towards, forced):
        if min_value is not None:
            assume(min_value <= forced)
        if max_value is not None:
            assume(forced <= max_value)
        # default shrink_towards param
        if shrink_towards is None:
            shrink_towards = 0

        data = fresh_data()
        assert (
            data.draw_integer(
                min_value, max_value, shrink_towards=shrink_towards, forced=forced
            )
            == forced
        )

        data = ConjectureData.for_buffer(data.buffer)
        assert (
            data.draw_integer(min_value, max_value, shrink_towards=shrink_towards)
            == forced
        )

    inner_test()


@pytest.mark.parametrize(
    "min_size_s, max_size_s",
    [
        (st.none(), st.none()),
        (st.integers(min_value=0), st.none()),
        (st.none(), st.integers(min_value=0)),
        (st.integers(min_value=0), st.integers(min_value=0)),
    ],
)
def test_forced_string(min_size_s, max_size_s):
    forced_s = st.text()
    intervals = unwrap_strategies(forced_s).element_strategy.intervals

    @given(min_size_s, max_size_s, forced_s)
    @settings(
        database=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    )
    def inner_test(min_size, max_size, forced):
        if min_size is None:
            min_size = 0

        assume(min_size <= len(forced))
        if max_size is not None:
            assume(len(forced) <= max_size)

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

    inner_test()


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
