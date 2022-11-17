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
from hypothesis.control import assume
from hypothesis.errors import FailedHealthCheck, InvalidArgument
from hypothesis.internal.compat import int_from_bytes
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.entropy import deterministic_PRNG
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
    run_state_machine_as_test,
)
from hypothesis.strategies._internal.lazy import LazyStrategy
from hypothesis.strategies._internal.strategies import SearchStrategy

from tests.common.utils import no_shrink

HEALTH_CHECK_SETTINGS = settings(max_examples=11, database=None)


def test_slow_generation_fails_a_health_check():
    @HEALTH_CHECK_SETTINGS
    @given(st.integers().map(lambda x: time.sleep(0.2)))
    def test(x):
        pass

    with raises(FailedHealthCheck):
        test()


def test_slow_generation_inline_fails_a_health_check():
    @HEALTH_CHECK_SETTINGS
    @given(st.data())
    def test(data):
        data.draw(st.integers().map(lambda x: time.sleep(0.2)))

    with raises(FailedHealthCheck):
        test()


def test_default_health_check_can_weaken_specific():
    import random

    @settings(HEALTH_CHECK_SETTINGS, suppress_health_check=HealthCheck.all())
    @given(st.lists(st.integers(), min_size=1))
    def test(x):
        random.choice(x)

    test()


def test_suppressing_filtering_health_check():
    forbidden = set()

    def unhealthy_filter(x):
        if len(forbidden) < 200:
            forbidden.add(x)
        return x not in forbidden

    @HEALTH_CHECK_SETTINGS
    @given(st.integers().filter(unhealthy_filter))
    def test1(x):
        raise ValueError()

    with raises(FailedHealthCheck):
        test1()

    forbidden = set()

    @settings(suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow])
    @given(st.integers().filter(unhealthy_filter))
    def test2(x):
        raise ValueError()

    with raises(ValueError):
        test2()


def test_filtering_everything_fails_a_health_check():
    @given(st.integers().filter(lambda x: False))
    @settings(database=None)
    def test(x):
        pass

    with raises(FailedHealthCheck) as e:
        test()
    assert "filter" in e.value.args[0]


class fails_regularly(SearchStrategy):
    def do_draw(self, data):
        b = int_from_bytes(data.draw_bytes(2))
        assume(b == 3)
        print("ohai")


def test_filtering_most_things_fails_a_health_check():
    @given(fails_regularly())
    @settings(database=None, phases=no_shrink)
    def test(x):
        pass

    with raises(FailedHealthCheck) as e:
        test()
    assert "filter" in e.value.args[0]


def test_large_data_will_fail_a_health_check():
    @given(st.none() | st.binary(min_size=10**5, max_size=10**5))
    @settings(database=None)
    def test(x):
        pass

    with raises(FailedHealthCheck) as e:
        test()
    assert "allowable size" in e.value.args[0]


def test_returning_non_none_is_forbidden():
    @given(st.integers())
    def a(x):
        return 1

    with raises(FailedHealthCheck):
        a()


def test_the_slow_test_health_check_can_be_disabled():
    @given(st.integers())
    @settings(deadline=None)
    def a(x):
        time.sleep(1000)

    a()


def test_the_slow_test_health_only_runs_if_health_checks_are_on():
    @given(st.integers())
    @settings(suppress_health_check=HealthCheck.all(), deadline=None)
    def a(x):
        time.sleep(1000)

    a()


def test_returning_non_none_does_not_fail_if_health_check_disabled():
    @given(st.integers())
    @settings(suppress_health_check=HealthCheck.all())
    def a(x):
        return 1

    a()


def test_large_base_example_fails_health_check():
    @given(st.binary(min_size=7000, max_size=7000))
    def test(b):
        pass

    with pytest.raises(FailedHealthCheck) as exc:
        test()

    assert str(HealthCheck.large_base_example) in str(exc.value)


def test_example_that_shrinks_to_overrun_fails_health_check():
    @given(st.binary(min_size=9000, max_size=9000) | st.none())
    def test(b):
        pass

    with pytest.raises(FailedHealthCheck) as exc:
        test()

    assert str(HealthCheck.large_base_example) in str(exc.value)


def test_it_is_an_error_to_suppress_non_iterables():
    with raises(InvalidArgument):
        settings(suppress_health_check=1)


def test_it_is_an_error_to_suppress_non_healthchecks():
    with raises(InvalidArgument):
        settings(suppress_health_check=[1])


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
    existing_draw_bits = ConjectureData.draw_bits

    # We need to make drawing data artificially slow in order to trigger this
    # effect. This isn't actually slow because time is fake in our CI, but
    # we need it to pretend to be.
    def draw_bits(self, n, forced=None):
        time.sleep(0.001)
        return existing_draw_bits(self, n, forced=forced)

    monkeypatch.setattr(ConjectureData, "draw_bits", draw_bits)

    with deterministic_PRNG():
        for _ in range(100):
            # Setting max_examples=11 ensures we have enough examples for the
            # health checks to finish running, but cuts the generation short
            # after that point to allow this test to run in reasonable time.
            @settings(database=None, max_examples=11, phases=[Phase.generate])
            @given(st.binary())
            def test(b):
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
                    lambda n: st.binary(min_size=n * 100, max_size=n * 100)
                )
            )
            def test(b):
                pass

            test()


class ReturningRuleMachine(RuleBasedStateMachine):
    @rule()
    def r(self):
        return "any non-None value"


class ReturningInitializeMachine(RuleBasedStateMachine):
    _ = rule()(lambda self: None)

    @initialize()
    def r(self):
        return "any non-None value"


class ReturningInvariantMachine(RuleBasedStateMachine):
    _ = rule()(lambda self: None)

    @invariant(check_during_init=True)
    def r(self):
        return "any non-None value"


@pytest.mark.parametrize(
    "cls", [ReturningRuleMachine, ReturningInitializeMachine, ReturningInvariantMachine]
)
def test_stateful_returnvalue_healthcheck(cls):
    with pytest.raises(FailedHealthCheck):
        run_state_machine_as_test(cls, settings=settings())
