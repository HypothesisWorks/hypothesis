# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from collections import defaultdict

from hypothesis import settings, strategies as st
from hypothesis.internal.observability import PredicateCounts
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    RuleStrategy,
    consumes,
    rule,
    run_state_machine_as_test,
)
from hypothesis.strategies._internal.featureflags import FeatureFlags


class Chain(RuleBasedStateMachine):
    a = Bundle("a")
    b = Bundle("b")

    @rule(target=a)
    def make_a(self):
        return 1

    @rule(target=b, x=a)
    def a_to_b(self, x):
        return x + 1

    @rule(x=b)
    def use_b(self, x):
        pass

    @rule(n=st.integers())
    def unrelated(self, n):
        pass


def enabled_rules(machine_type, disabled):
    # Every bundle is non-empty, so that only the swarm flags decide.
    machine = machine_type()
    machine._observability_predicates = defaultdict(PredicateCounts)
    for name in ("a", "b", "things"):
        machine.bundle(name).append(None)
    strat = RuleStrategy(machine)
    strat._feature_flags = FeatureFlags(disabled=disabled)
    return {r.function.__name__ for r in strat.rules if strat._rule_is_enabled(r)}


def test_dependencies_are_found():
    deps = RuleStrategy._swarm_dependencies_for(Chain)
    assert {k: {r.function.__name__ for r in v} for k, v in deps.items()} == {
        "make_a": {"a_to_b"},
        "a_to_b": {"use_b"},
    }


def test_producers_of_an_enabled_consumer_are_enabled():
    # The closure is transitive: use_b needs a_to_b, which needs make_a.
    assert enabled_rules(Chain, disabled=["make_a", "a_to_b", "unrelated"]) == {
        "make_a",
        "a_to_b",
        "use_b",
    }


def test_producers_stay_disabled_when_no_consumer_is_enabled():
    assert enabled_rules(Chain, disabled=["make_a", "a_to_b", "use_b"]) == {"unrelated"}


def test_closure_does_not_enable_consumers():
    assert enabled_rules(Chain, disabled=["a_to_b", "use_b", "unrelated"]) == {"make_a"}


class Cycle(RuleBasedStateMachine):
    things = Bundle("things")

    @rule(target=things)
    def seed(self):
        return 0

    @rule(target=things, x=consumes(things))
    def step(self, x):
        return x + 1

    @rule(target=things, x=things)
    def other(self, x):
        return x


def test_cycles_terminate():
    # step and other each consume from and produce into the same bundle.
    assert enabled_rules(Cycle, disabled=["seed", "step"]) == {
        "seed",
        "step",
        "other",
    }
    assert enabled_rules(Cycle, disabled=["seed", "step", "other"]) == set()


class NoBundles(RuleBasedStateMachine):
    @rule()
    def f(self):
        pass

    @rule(n=st.integers())
    def g(self, n):
        pass


def test_no_bundles_no_dependencies():
    assert RuleStrategy._swarm_dependencies_for(NoBundles) == {}
    assert enabled_rules(NoBundles, disabled=["f"]) == {"g"}


class CountingChain(Chain):
    # The producer is the only way to make the consumer runnable, so the
    # consumer can run in a test case only if swarm testing (with the closure)
    # did not leave make_a disabled.
    used = 0

    @rule(x=Chain.a)
    def use_a(self, x):
        type(self).used += 1


def test_consumers_still_run_under_swarm_testing():
    CountingChain.used = 0
    run_state_machine_as_test(
        CountingChain, settings=settings(max_examples=50, database=None)
    )
    assert CountingChain.used > 0
