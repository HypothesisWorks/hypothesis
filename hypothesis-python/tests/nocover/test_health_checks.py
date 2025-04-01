# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import time

import pytest
from pytest import raises

from hypothesis import HealthCheck, Phase, given, settings, strategies as st
from hypothesis.errors import FailedHealthCheck
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.engine import BUFFER_SIZE
from hypothesis.internal.entropy import deterministic_PRNG
from hypothesis.strategies._internal.lazy import LazyStrategy

pytestmark = pytest.mark.skipif(
    settings._current_profile == "crosshair", reason="slow - large number of symbolics"
)

large_strategy = st.binary(min_size=7000, max_size=7000)
too_large_strategy = st.tuples(large_strategy, large_strategy)


def test_large_data_will_fail_a_health_check():
    @given(st.none() | too_large_strategy)
    @settings(database=None)
    def test(x):
        pass

    with raises(FailedHealthCheck) as e:
        test()
    assert "allowable size" in e.value.args[0]


def test_large_base_example_fails_health_check():
    @given(large_strategy)
    def test(b):
        pass

    with pytest.raises(FailedHealthCheck) as exc:
        test()

    assert str(HealthCheck.large_base_example) in str(exc.value)


def test_example_that_shrinks_to_overrun_fails_health_check():
    @given(too_large_strategy | st.none())
    def test(b):
        pass

    with pytest.raises(FailedHealthCheck) as exc:
        test()

    assert str(HealthCheck.large_base_example) in str(exc.value)


slow_down_init = True


def slow_init_integers(*args, **kwargs):
    # This mimics st.characters() or st.text(), which perform some
    # expensive Unicode calculations when the cache is empty.
    global slow_down_init
    if slow_down_init:
        time.sleep(0.5)  # We monkeypatch time, so this is fast
        slow_down_init = False
    return st.integers(*args, **kwargs)


@given(st.data())
def test_lazy_slow_initialization_issue_2108_regression(data):
    # Slow init in strategies wrapped in a LazyStrategy, inside an interactive draw,
    # should be attributed to drawing from the strategy (not the test function).
    # Specifically, this used to fail with a DeadlineExceeded error.
    data.draw(LazyStrategy(slow_init_integers, (), {}))


def test_does_not_trigger_health_check_on_simple_strategies(monkeypatch):
    existing_draw = ConjectureData.draw_integer

    # We need to make drawing data artificially slow in order to trigger this
    # effect. This isn't actually slow because time is fake in our CI, but
    # we need it to pretend to be.
    def draw_integer(*args, **kwargs):
        time.sleep(0.001)
        return existing_draw(*args, **kwargs)

    monkeypatch.setattr(ConjectureData, "draw_integer", draw_integer)

    with deterministic_PRNG():
        for _ in range(100):
            # Setting max_examples=11 ensures we have enough examples for the
            # health checks to finish running, but cuts the generation short
            # after that point to allow this test to run in reasonable time.
            @settings(database=None, max_examples=11, phases=[Phase.generate])
            @given(st.integers())
            def test(n):
                pass

            test()


def test_does_not_trigger_health_check_when_most_examples_are_small(monkeypatch):
    with deterministic_PRNG():
        for _ in range(100):
            # Setting max_examples=11 ensures we have enough examples for the
            # health checks to finish running, but cuts the generation short
            # after that point to allow this test to run in reasonable time.
            @settings(database=None, max_examples=11, phases=[Phase.generate])
            @given(
                st.integers(0, 100).flatmap(
                    lambda n: st.binary(
                        min_size=min(n * 100, BUFFER_SIZE), max_size=n * 100
                    )
                )
            )
            def test(b):
                pass

            test()
