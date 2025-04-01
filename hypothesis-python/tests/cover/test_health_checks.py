# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re
import time

import pytest

from hypothesis import HealthCheck, given, settings, strategies as st
from hypothesis.control import assume, current_build_context
from hypothesis.errors import FailedHealthCheck, InvalidArgument
from hypothesis.internal.compat import int_from_bytes
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
    run_state_machine_as_test,
)
from hypothesis.strategies._internal.strategies import SearchStrategy

from tests.common.utils import Why, no_shrink, xfail_on_crosshair

HEALTH_CHECK_SETTINGS = settings(
    max_examples=11, database=None, suppress_health_check=()
)


def test_slow_generation_fails_a_health_check():
    @settings(HEALTH_CHECK_SETTINGS, deadline=200)
    @given(st.integers().map(lambda x: time.sleep(0.2)))
    def test(x):
        pass

    with pytest.raises(FailedHealthCheck):
        test()


def test_slow_generation_inline_fails_a_health_check():
    @settings(HEALTH_CHECK_SETTINGS, deadline=200)
    @given(st.data())
    def test(data):
        data.draw(st.integers().map(lambda x: time.sleep(0.2)))

    with pytest.raises(FailedHealthCheck):
        test()


def test_default_health_check_can_weaken_specific():
    import random

    @settings(HEALTH_CHECK_SETTINGS, suppress_health_check=list(HealthCheck))
    @given(st.lists(st.integers(), min_size=1))
    def test(x):
        random.choice(x)

    test()


@pytest.mark.skipif(settings._current_profile == "crosshair", reason="nondeterministic")
def test_suppressing_filtering_health_check():
    forbidden = set()

    def unhealthy_filter(x):
        if len(forbidden) < 200:
            forbidden.add(x)
        return x not in forbidden

    @HEALTH_CHECK_SETTINGS
    @given(st.integers().filter(unhealthy_filter))
    def test1(x):
        raise ValueError

    with pytest.raises(FailedHealthCheck):
        test1()

    forbidden = set()

    @settings(suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow])
    @given(st.integers().filter(unhealthy_filter))
    def test2(x):
        raise ValueError

    with pytest.raises(ValueError):
        test2()


def test_filtering_everything_fails_a_health_check():
    @given(st.integers().filter(lambda x: False))
    @settings(database=None, suppress_health_check=())
    def test(x):
        pass

    with pytest.raises(FailedHealthCheck, match="filter"):
        test()


class fails_regularly(SearchStrategy):
    def do_draw(self, data):
        b = int_from_bytes(data.draw_bytes(2, 2))
        assume(b == 3)
        print("ohai")


def test_filtering_most_things_fails_a_health_check():
    @given(fails_regularly())
    @settings(database=None, phases=no_shrink, suppress_health_check=())
    def test(x):
        if current_build_context().data.provider.avoid_realization:
            pytest.skip("symbolic backends can filter efficiently!")

    with pytest.raises(FailedHealthCheck, match="filter"):
        test()


def test_returning_non_none_is_forbidden():
    @given(st.integers())
    def a(x):
        return 1

    with pytest.raises(FailedHealthCheck):
        a()


def test_the_slow_test_health_check_can_be_disabled():
    @given(st.integers())
    @settings(deadline=None)
    def a(x):
        time.sleep(1000)

    a()


def test_the_slow_test_health_only_runs_if_health_checks_are_on():
    @given(st.integers())
    @settings(suppress_health_check=list(HealthCheck), deadline=None)
    def a(x):
        time.sleep(1000)

    a()


class sample_test_runner:
    @given(st.none())
    def test(self, _):
        pass


def test_differing_executors_fails_health_check():
    sample_test_runner().test()
    msg = re.escape(str(HealthCheck.differing_executors))
    with pytest.raises(FailedHealthCheck, match=msg):
        sample_test_runner().test()


def test_it_is_an_error_to_suppress_non_iterables():
    with pytest.raises(InvalidArgument):
        settings(suppress_health_check=1)


def test_it_is_an_error_to_suppress_non_healthchecks():
    with pytest.raises(InvalidArgument):
        settings(suppress_health_check=[1])


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


def test_nested_given_raises_healthcheck():
    @given(st.integers())
    def f(n1):
        @given(st.integers())
        def g(n2):
            pass

        g()

    with pytest.raises(FailedHealthCheck):
        f()


def test_triply_nested_given_raises_healthcheck():
    @given(st.integers())
    @settings(max_examples=10)
    def f(n1):

        @given(st.integers())
        @settings(max_examples=10)
        def g(n2):

            @given(st.integers())
            @settings(max_examples=10)
            def h(n3):
                pass

            h()

        g()

    with pytest.raises(FailedHealthCheck):
        f()


@xfail_on_crosshair(Why.nested_given)
def test_can_suppress_nested_given():
    @given(st.integers())
    @settings(suppress_health_check=[HealthCheck.nested_given], max_examples=5)
    def f(n1):

        @given(st.integers())
        @settings(max_examples=5)
        def g(n2):
            pass

        g()

    f()


def test_cant_suppress_nested_given_on_inner():
    # nested_given has to be suppressed at the function right above the nesting.
    # this isn't a principled design choice, but a limitation of how we access
    # the current settings.
    @given(st.integers())
    @settings(max_examples=5)
    def f(n1):

        @given(st.integers())
        @settings(suppress_health_check=[HealthCheck.nested_given], max_examples=5)
        def g(n2):
            pass

        g()

    with pytest.raises(FailedHealthCheck):
        f()


@xfail_on_crosshair(Why.nested_given)
def test_suppress_triply_nested_given():
    # both suppressions are necessary here
    @given(st.integers())
    @settings(suppress_health_check=[HealthCheck.nested_given], max_examples=5)
    def f(n1):

        @given(st.integers())
        @settings(suppress_health_check=[HealthCheck.nested_given], max_examples=5)
        def g(n2):

            @given(st.integers())
            @settings(max_examples=5)
            def h(n3):
                pass

            h()

        g()

    f()
