# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import contextlib
import sys
import threading
import unittest

import pytest

from hypothesis import Phase, assume, settings, strategies as st
from hypothesis.internal import locbias
from hypothesis.stateful import (
    RuleBasedStateMachine,
    precondition,
    rule,
    run_state_machine_as_test,
)

from tests.common.utils import skipif_emscripten
from tests.conjecture.test_provider import PrngProvider, temp_register_backend

# The LOC tests measure our own random backend; when the whole suite runs
# under another backend (e.g. crosshair), LOC weighting is off by design.
pytestmark = pytest.mark.skipif(
    settings().backend != "hypothesis",
    reason="LOC weighting applies only to the default backend",
)

TRACERS = [False] + ([True] if hasattr(sys, "monitoring") else [])


@pytest.fixture(params=TRACERS, ids=lambda m: "monitoring" if m else "profile")
def fresh(monkeypatch, request):
    # Measure from scratch, with a longer probe for stable estimates.
    monkeypatch.setattr(locbias, "_MONITORING", request.param)
    monkeypatch.setattr(locbias, "_PROFILES", {})
    monkeypatch.setattr(locbias, "_PROBED", set())
    monkeypatch.setattr(locbias, "PROBE_EXAMPLES", 50)
    monkeypatch.setattr(locbias, "MIN_MAX_EXAMPLES", 20)


def weights(samples, names):
    p = locbias.LOCProfile()
    p.samples = samples
    return p.weights(tuple(names))


def test_weights_match_worked_example_from_paper(monkeypatch):
    # Mean LOC of 0, 30 and 20 give probabilities 0.20, 0.48 and 0.32.
    monkeypatch.setattr(locbias, "FLOOR", 0.0)
    w = weights({"a": [0, 0], "b": [20, 40], "c": [20]}, "abc")
    scale = 1 - locbias.UNIFORM_MIX
    assert w == pytest.approx({0: 0.20 * scale, 1: 0.48 * scale, 2: 0.32 * scale})


def test_floor_gives_every_rule_a_minimum_share():
    names = ["sync", "upload", "newstorage", "idle"]
    w = weights({"sync": [1730], "upload": [3], "newstorage": [30], "idle": [0]}, names)
    scale = 1 - locbias.UNIFORM_MIX
    assert min(w.values()) >= locbias.FLOOR / len(names) * scale - 1e-12
    assert sum(w.values()) == pytest.approx(scale)
    assert w[0] == max(w.values())


def test_unsampled_rules_get_the_average_weight():
    w = weights({"b": [10], "c": [30]}, ["never_ran", "b", "c"])
    assert w[0] == pytest.approx(w[1] + (w[2] - w[1]) / 2)


def test_no_information_means_no_weights():
    assert weights({}, "ab") is None
    assert weights({"a": [0], "b": [0]}, "ab") is None
    assert weights({"a": [3]}, "a") is None


def big(x):
    # Padding so that this function is much longer than `small`.
    y = x
    y += 1
    y += 1
    y += 1
    y += 1
    y += 1
    y += 1
    y += 1
    y += 1
    y += 1
    y += 1
    y += 1
    y += 1
    y += 1
    y += 1
    y += 1
    y += 1
    y += 1
    return y


def small(x):
    return x


def make_machine(counts):
    class Machine(RuleBasedStateMachine):
        ready = False

        @rule()
        def calls_big(self):
            counts["big"] += locbias.probing() is None  # i.e. not in the probe
            big(1)

        @rule()
        def calls_small(self):
            counts["small"] += locbias.probing() is None
            small(1)
            self.ready = True

        @rule(x=st.integers())
        def calls_nothing(self, x):
            pass

        @rule(x=st.integers())
        def usually_rejects(self, x):
            assume(x == 0)
            big(x)

        @rule()
        @precondition(lambda self: self.ready)
        def precondition_inside_rule(self):
            big(1)

        @precondition(lambda self: self.ready)
        @rule(d=st.data())
        def draws_then_calls_small(self, d):
            d.draw(st.lists(st.integers()))
            small(1)

    return Machine


def test_probe_measures_code_under_each_rule(fresh):
    Machine = make_machine({"big": 0, "small": 0})
    run_state_machine_as_test(Machine, settings=settings(max_examples=60))
    loc = locbias._PROFILES[Machine].mean_loc()
    assert loc["calls_nothing"] == 0
    assert loc["calls_small"] == 2
    assert loc["calls_big"] == 21
    # Engine and stdlib code run on behalf of data.draw() is not counted.
    assert loc.get("draws_then_calls_small", 2) == 2
    # ... but the rule body beneath Hypothesis's precondition wrapper is.
    assert loc.get("precondition_inside_rule", 21) == 21
    # Executions cut short by assume() are not averaged in as zeros.
    assert loc.get("usually_rejects", 21) == 21


def test_heavier_rules_run_more_often(fresh):
    counts = {"big": 0, "small": 0}
    Machine = make_machine(counts)
    run_state_machine_as_test(Machine, settings=settings(max_examples=150))
    assert counts["big"] > 2 * counts["small"]


def test_probe_runs_once_per_process(fresh):
    runs = []

    class Machine(RuleBasedStateMachine):
        def __init__(self):
            super().__init__()
            runs.append(locbias.probing() is None)

        @rule()
        def a(self):
            big(0)

        @rule()
        def b(self):
            pass

    run_state_machine_as_test(
        Machine, settings=settings(max_examples=80, database=None)
    )
    # Invalid test cases do not count towards max_examples, hence >=.
    assert runs.count(False) >= locbias.PROBE_EXAMPLES
    assert runs.count(True) >= 80
    # The weights are measured once per process.
    runs.clear()
    run_state_machine_as_test(Machine, settings=settings(max_examples=80))
    assert all(runs)


@pytest.mark.parametrize(
    "s",
    [
        settings(max_examples=10),
        settings(max_examples=100, phases=[Phase.explicit, Phase.reuse]),
    ],
)
def test_no_probe_without_room_to_generate(fresh, s):
    class Machine(RuleBasedStateMachine):
        @rule()
        def a(self):
            big(0)

    with contextlib.suppress(unittest.SkipTest):
        run_state_machine_as_test(Machine, settings=s)
    assert Machine not in locbias._PROFILES


def test_no_probe_for_other_backends(fresh):
    class Machine(RuleBasedStateMachine):
        @rule()
        def a(self):
            big(0)

        @rule()
        def b(self):
            small(0)

    with temp_register_backend("loc-test-prng", PrngProvider):
        run_state_machine_as_test(
            Machine, settings=settings(max_examples=60, backend="loc-test-prng")
        )
    assert Machine not in locbias._PROFILES


def test_can_be_disabled(fresh, monkeypatch):
    monkeypatch.setattr(locbias, "ENABLED", False)
    Machine = make_machine({"big": 0, "small": 0})
    run_state_machine_as_test(Machine, settings=settings(max_examples=60))
    assert Machine not in locbias._PROFILES


def test_failures_are_still_found_and_shrunk(fresh):
    class Machine(RuleBasedStateMachine):
        n = 0

        @rule()
        def inc(self):
            self.n += big(0) - 16
            assert self.n < 3

        @rule()
        def noop(self):
            small(0)

    with pytest.raises(AssertionError) as err:
        run_state_machine_as_test(Machine, settings=settings(max_examples=200))
    steps = [s for s in "\n".join(err.value.__notes__).splitlines() if "state." in s]
    assert steps == ["state.inc()"] * 3 + ["state.teardown()"]


def test_a_factory_that_fails_in_the_probe_is_left_unweighted(fresh):
    Machine = make_machine({"big": 0, "small": 0})

    def factory():
        if locbias.probing() is not None:
            raise ValueError
        return Machine()

    run_state_machine_as_test(factory, settings=settings(max_examples=60))
    assert not locbias._PROFILES


ALLOWED = {"heavy": True, "cheap2": True}


class FallbackMachine(RuleBasedStateMachine):
    @precondition(lambda self: ALLOWED["heavy"])
    @rule()
    def h1(self):
        big(0)

    @precondition(lambda self: ALLOWED["heavy"])
    @rule()
    def h2(self):
        big(0)

    @rule()
    def cheap(self):
        small(0)

    @precondition(lambda self: ALLOWED["cheap2"])
    @rule()
    def cheap2(self):
        small(0)


@pytest.mark.parametrize("cheap2", [True, False])
def test_weighted_selection_falls_back_when_heavy_rules_are_invalid(
    fresh, monkeypatch, cheap2
):
    # Measure with every rule allowed, then forbid the heavy ones: rejection
    # sampling on the (heavily weighted) index then fails, and the explicit
    # choice among the remaining rules is used.
    monkeypatch.setattr(FallbackMachine, "_cheap_runs", 0, raising=False)
    monkeypatch.setitem(ALLOWED, "heavy", True)
    monkeypatch.setitem(ALLOWED, "cheap2", True)
    run_state_machine_as_test(FallbackMachine, settings=settings(max_examples=60))
    assert locbias._PROFILES[FallbackMachine].mean_loc()["h1"] == 21
    monkeypatch.setitem(ALLOWED, "heavy", False)
    monkeypatch.setitem(ALLOWED, "cheap2", cheap2)
    run_state_machine_as_test(
        FallbackMachine, settings=settings(max_examples=60, database=None)
    )


def gen(n):
    # Padding so that this generator is longer than `small`.
    x = 0
    x += 1
    x += 1
    yield from range(n)


def raises():
    raise ValueError


def catches():
    try:
        raises()
    except ValueError:
        pass
    return small(0)


def background_big():
    big(0)


def background_small():
    small(0)


def test_generators_and_exceptions_are_measured(fresh):
    # Every way of entering and leaving a frame: a generator suspended and
    # resumed, one closed early (GeneratorExit thrown in), and an exception
    # unwinding a frame.
    class Machine(RuleBasedStateMachine):
        @rule()
        def iterates(self):
            sum(gen(3))

        @rule()
        def abandons(self):
            g = gen(3)
            next(g)
            g.close()
            small(0)

        @rule()
        def handles(self):
            catches()

    run_state_machine_as_test(Machine, settings=settings(max_examples=60))
    loc = locbias._PROFILES[Machine].mean_loc()
    assert loc["iterates"] == 6
    assert loc["abandons"] == 6 + 2
    assert loc["handles"] == 6 + 2 + 2


@skipif_emscripten
def test_other_threads_are_not_measured(fresh):
    # Code running at the same time on another thread must not count.
    class Machine(RuleBasedStateMachine):
        @rule()
        def thread_big(self):
            t = threading.Thread(target=background_big)
            t.start()
            t.join()

        @rule()
        def thread_small(self):
            t = threading.Thread(target=background_small)
            t.start()
            t.join()

    run_state_machine_as_test(Machine, settings=settings(max_examples=60))
    loc = locbias._PROFILES[Machine].mean_loc()
    # The threading module's own code counts, as library code always does,
    # but nothing that runs on the other thread does: if it did, thread_big
    # would come out about 19 lines (big minus small) above thread_small.
    # Which paths start() and join() take depends on timing, so allow a
    # little noise (on PyPy the threading module is several hundred lines).
    assert loc["thread_small"] > 0
    assert abs(loc["thread_big"] - loc["thread_small"]) < 5
