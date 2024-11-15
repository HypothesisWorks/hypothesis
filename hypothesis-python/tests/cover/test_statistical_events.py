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
import traceback

import pytest

from hypothesis import (
    HealthCheck,
    assume,
    event,
    example,
    given,
    reject,
    settings,
    stateful,
    strategies as st,
    target,
)
from hypothesis.statistics import collector, describe_statistics


def call_for_statistics(test_function):
    result = []
    with collector.with_value(result.append):
        try:
            test_function()
        except Exception:
            traceback.print_exc()
    assert len(result) == 1, result
    return result[0]


def unique_events(stats):
    return set(sum((t["events"] for t in stats["generate-phase"]["test-cases"]), []))


def test_notes_hard_to_satisfy():
    @given(st.integers())
    @settings(suppress_health_check=list(HealthCheck))
    def test(i):
        assume(i == 13)

    stats = call_for_statistics(test)
    assert "satisfied assumptions" in stats["stopped-because"]


def test_can_callback_with_a_string():
    @given(st.integers())
    def test(i):
        event("hi")

    stats = call_for_statistics(test)
    assert any("hi" in s for s in unique_events(stats))


counter = 0
seen = []


class Foo:
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    def __hash__(self):
        return 0

    def __str__(self):
        seen.append(self)
        global counter
        counter += 1
        return f"COUNTER {counter}"


def test_formats_are_evaluated_only_once():
    global counter
    counter = 0

    @given(st.integers())
    def test(i):
        event(Foo())

    stats = call_for_statistics(test)
    assert "COUNTER 1" in unique_events(stats)
    assert "COUNTER 2" not in unique_events(stats)


def test_does_not_report_on_examples():
    @example("hi")
    @given(st.integers())
    def test(i):
        if isinstance(i, str):
            event("boo")

    stats = call_for_statistics(test)
    assert not unique_events(stats)


def test_exact_timing():
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(st.integers())
    def test(i):
        time.sleep(0.5)

    stats = describe_statistics(call_for_statistics(test))
    assert "~ 500ms" in stats


def test_apparently_instantaneous_tests():
    time.freeze()

    @given(st.integers())
    def test(i):
        pass

    stats = describe_statistics(call_for_statistics(test))
    assert "< 1ms" in stats


def test_flaky_exit():
    first = True

    @settings(derandomize=True)
    @given(st.integers())
    def test(i):
        nonlocal first
        if i > 1001:
            if first:
                first = False
                print("Hi")
                raise AssertionError

    stats = call_for_statistics(test)
    assert stats["stopped-because"] == "test was flaky"


@pytest.mark.parametrize("draw_delay", [False, True])
@pytest.mark.parametrize("test_delay", [False, True])
def test_draw_timing(draw_delay, test_delay):
    time.freeze()

    @st.composite
    def s(draw):
        if draw_delay:
            time.sleep(0.05)
        draw(st.integers())

    @given(s())
    def test(_):
        if test_delay:
            time.sleep(0.05)

    stats = describe_statistics(call_for_statistics(test))
    if not draw_delay:
        assert "< 1ms" in stats
    else:
        match = re.search(r"of which ~ (?P<gentime>\d+)", stats)
        assert 49 <= int(match.group("gentime")) <= 51


def test_has_lambdas_in_output():
    @settings(max_examples=100, database=None)
    @given(st.integers().filter(lambda x: x % 2 == 0))
    def test(i):
        pass

    stats = call_for_statistics(test)
    assert any("lambda x: x % 2 == 0" in e for e in unique_events(stats))


def test_stops_after_x_shrinks(monkeypatch):
    # the max_shrinks argument is deprecated, but we still stop after some
    # number - which we can reduce to zero to check that this works.
    from hypothesis.internal.conjecture import engine

    monkeypatch.setattr(engine, "MAX_SHRINKS", 0)

    @given(st.integers(min_value=0))
    def test(n):
        assert n < 10

    stats = call_for_statistics(test)
    assert "shrunk example" in stats["stopped-because"]


def test_stateful_states_are_deduped():
    class DemoStateMachine(stateful.RuleBasedStateMachine):
        Stuff = stateful.Bundle("stuff")

        @stateful.rule(target=Stuff, name=st.text())
        def create_stuff(self, name):
            return name

        @stateful.rule(item=Stuff)
        def do(self, item):
            return

    stats = call_for_statistics(DemoStateMachine.TestCase().runTest)
    stats = unique_events(stats)
    stats = [s for s in stats if not s.startswith("invalid because: (internal)")]
    assert len(stats) <= 2


def test_stateful_with_one_of_bundles_states_are_deduped():
    class DemoStateMachine(stateful.RuleBasedStateMachine):
        Things = stateful.Bundle("things")
        Stuff = stateful.Bundle("stuff")
        StuffAndThings = Things | Stuff

        @stateful.rule(target=Things, name=st.text())
        def create_thing(self, name):
            return name

        @stateful.rule(target=Stuff, name=st.text())
        def create_stuff(self, name):
            return name

        @stateful.rule(item=StuffAndThings)
        def do(self, item):
            return

    stats = call_for_statistics(DemoStateMachine.TestCase().runTest)
    stats = unique_events(stats)
    stats = [s for s in stats if not s.startswith("invalid because: (internal)")]
    assert len(stats) <= 4


def test_statistics_for_threshold_problem():
    @settings(max_examples=100, database=None)
    @given(st.floats(min_value=0, allow_infinity=False))
    def threshold(error):
        target(error, label="error")
        assert error <= 10
        target(0.0, label="never in failing example")

    stats = call_for_statistics(threshold)
    assert "  - Highest target scores:" in describe_statistics(stats)
    assert "never in failing example" in describe_statistics(stats)
    # Check that we report far-from-threshold failing examples
    assert stats["targets"]["error"] > 10


def test_statistics_with_events_and_target():
    @given(st.integers(0, 10_000))
    def test(value):
        event(value)
        target(float(value), label="a target")

    stats = describe_statistics(call_for_statistics(test))
    assert "- Events:" in stats
    assert "- Highest target score: " in stats


@given(st.booleans())
def test_event_with_non_weakrefable_keys(b):
    event((b,))


def test_assume_adds_event_with_function_origin():
    @given(st.integers())
    def very_distinguishable_name(n):
        assume(n > 100)

    stats = call_for_statistics(very_distinguishable_name)

    for tc in stats["generate-phase"]["test-cases"]:
        for e in tc["events"]:
            assert "failed to satisfy assume() in very_distinguishable_name" in e


def test_reject_adds_event_with_function_origin():
    @given(st.integers())
    def very_distinguishable_name(n):
        if n > 100:
            reject()

    stats = call_for_statistics(very_distinguishable_name)

    for tc in stats["generate-phase"]["test-cases"]:
        for e in tc["events"]:
            assert "reject() in very_distinguishable_name" in e
