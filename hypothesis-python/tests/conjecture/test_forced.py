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
from hypothesis import HealthCheck, assume, example, given, settings
from hypothesis.internal.conjecture import utils as cu
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.floats import float_to_lex
from hypothesis.internal.floats import SIGNALING_NAN, SMALLEST_SUBNORMAL

from tests.conjecture.common import (
    draw_boolean_kwargs,
    draw_bytes_kwargs,
    draw_float_kwargs,
    draw_integer_kwargs,
    draw_string_kwargs,
    fresh_data,
)


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


@example({"p": 1e-19, "forced": True})  # 64 bit p
@example({"p": 3e-19, "forced": True})  # 62 bit p
@given(draw_boolean_kwargs(use_forced=True))
def test_forced_boolean(kwargs):
    forced = kwargs["forced"]

    data = fresh_data()
    assert data.draw_boolean(**kwargs) == forced

    # now make sure the written buffer reproduces the forced value, even without
    # specifying forced=.
    del kwargs["forced"]
    data = ConjectureData.for_buffer(data.buffer)
    assert data.draw_boolean(**kwargs) == forced


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
def test_forced_integer(use_min_value, use_max_value, use_shrink_towards, use_weights):
    healthchecks = list(HealthCheck) * (use_min_value and use_max_value and use_weights)

    @settings(derandomize=True, suppress_health_check=healthchecks)
    @given(
        draw_integer_kwargs(
            use_min_value=use_min_value,
            use_max_value=use_max_value,
            use_shrink_towards=use_shrink_towards,
            use_weights=use_weights,
            use_forced=True,
        )
    )
    def test(kwargs):
        forced = kwargs["forced"]

        data = fresh_data()
        assert data.draw_integer(**kwargs) == forced

        del kwargs["forced"]
        data = ConjectureData.for_buffer(data.buffer)
        assert data.draw_integer(**kwargs) == forced

    test()


@pytest.mark.parametrize("use_min_size", [True, False])
@pytest.mark.parametrize("use_max_size", [True, False])
def test_forced_string(use_min_size, use_max_size):
    @given(
        draw_string_kwargs(
            use_min_size=use_min_size, use_max_size=use_max_size, use_forced=True
        )
    )
    def test(kwargs):
        forced = kwargs["forced"]

        data = fresh_data()
        assert data.draw_string(**kwargs) == forced

        del kwargs["forced"]
        data = ConjectureData.for_buffer(data.buffer)
        assert data.draw_string(**kwargs) == forced

    test()


@given(st.data())
def test_forced_bytes(data):
    kwargs = data.draw(draw_bytes_kwargs(use_forced=True))
    forced = kwargs["forced"]

    data = fresh_data()
    assert data.draw_bytes(**kwargs) == forced

    del kwargs["forced"]
    data = ConjectureData.for_buffer(data.buffer)
    assert data.draw_bytes(**kwargs) == forced


@pytest.mark.parametrize("use_min_value", [True, False])
@pytest.mark.parametrize("use_max_value", [True, False])
def test_forced_floats(use_min_value, use_max_value):
    @example({"forced": 0.0})
    @example({"forced": -0.0})
    @example({"forced": 1.0})
    @example({"forced": 1.2345})
    @example({"forced": SMALLEST_SUBNORMAL})
    @example({"forced": -SMALLEST_SUBNORMAL})
    @example({"forced": 100 * SMALLEST_SUBNORMAL})
    @example({"forced": math.nan})
    @example({"forced": -math.nan})
    @example({"forced": SIGNALING_NAN})
    @example({"forced": -SIGNALING_NAN})
    @example({"forced": 1e999})
    @example({"forced": -1e999})
    # previously errored on our {pos, neg}_clamper logic not considering nans.
    @example(
        {"min_value": -1 * math.inf, "max_value": -1 * math.inf, "forced": math.nan}
    )
    @given(
        draw_float_kwargs(
            use_min_value=use_min_value, use_max_value=use_max_value, use_forced=True
        )
    )
    def test(kwargs):
        # TODO intentionally avoid triggering a bug with forcing nan values
        # while both min and max value have the opposite sign.
        # Once we fix the aforementioned bug we can remove this intentional
        # weakening of the test.
        assume(not math.isnan(kwargs["forced"]))

        forced = kwargs["forced"]

        data = fresh_data()
        drawn = data.draw_float(**kwargs)
        # Bitwise equality check to handle nan, snan, -nan, +0, -0, etc.
        assert math.copysign(1, drawn) == math.copysign(1, forced)
        assert float_to_lex(abs(drawn)) == float_to_lex(abs(forced))

        del kwargs["forced"]
        data = ConjectureData.for_buffer(data.buffer)
        drawn = data.draw_float(**kwargs)
        assert math.copysign(1, drawn) == math.copysign(1, forced)
        assert float_to_lex(abs(drawn)) == float_to_lex(abs(forced))

    test()


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
def test_forced_floats_with_nan(sign, min_value, max_value):
    # nans with a sign opposite of both bounds previously gave us trouble
    # trying to use float clampers that didn't exist when drawing.
    data = fresh_data()
    data.draw_float(min_value=min_value, max_value=max_value, forced=sign * math.nan)
