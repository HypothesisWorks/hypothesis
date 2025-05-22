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
import textwrap

import pytest

from hypothesis import (
    assume,
    event,
    example,
    given,
    note,
    seed,
    settings,
    strategies as st,
    target,
)
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.internal.compat import PYPY
from hypothesis.internal.coverage import IN_COVERAGE_TESTS
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    rule,
    run_state_machine_as_test,
)

from tests.common.utils import Why, capture_observations, xfail_on_crosshair


@seed("deterministic so we don't miss some combination of features")
@example(l=[1], a=0, x=4, data=None)
# explicitly set max_examples=100 to override our lower example limit for coverage tests.
@settings(database=InMemoryExampleDatabase(), deadline=None, max_examples=100)
@given(st.lists(st.integers()), st.integers(), st.integers(), st.data())
def do_it_all(l, a, x, data):
    event(f"{x%2=}")
    target(x % 5, label="x%5")
    assume(a % 9)
    assume(len(l) > 0)
    if data:
        data.draw(st.text("abcdef", min_size=a % 3), label="interactive")
    1 / ((x or 1) % 7)


@xfail_on_crosshair(Why.other, strict=False)  # flakey BackendCannotProceed ??
def test_observability():
    with capture_observations() as ls:
        with pytest.raises(ZeroDivisionError):
            do_it_all()
        with pytest.raises(ZeroDivisionError):
            do_it_all()

    infos = [t for t in ls if t["type"] == "info"]
    assert len(infos) == 2
    assert {t["title"] for t in infos} == {"Hypothesis Statistics"}

    testcases = [t for t in ls if t["type"] == "test_case"]
    assert len(testcases) > 50
    assert {t["property"] for t in testcases} == {do_it_all.__name__}
    assert len({t["run_start"] for t in testcases}) == 2
    assert {t["status"] for t in testcases} == {"gave_up", "passed", "failed"}
    for t in testcases:
        if t["status"] != "gave_up":
            assert t["timing"]
            assert ("interactive" in t["arguments"]) == (
                "generate:interactive" in t["timing"]
            )


@xfail_on_crosshair(Why.other)
def test_capture_unnamed_arguments():
    @given(st.integers(), st.floats(), st.data())
    def f(v1, v2, data):
        data.draw(st.booleans())

    with capture_observations() as observations:
        f()

    test_cases = [tc for tc in observations if tc["type"] == "test_case"]
    for test_case in test_cases:
        assert list(test_case["arguments"].keys()) == [
            "v1",
            "v2",
            "data",
            "Draw 1",
        ], test_case


@pytest.mark.skipif(
    PYPY or IN_COVERAGE_TESTS, reason="explain phase requires sys.settrace pre-3.12"
)
def test_failure_includes_explain_phase_comments():
    @given(st.integers(), st.integers())
    @settings(database=None)
    def test_fails(x, y):
        if x:
            raise AssertionError

    with (
        capture_observations() as observations,
        pytest.raises(AssertionError),
    ):
        test_fails()

    test_cases = [tc for tc in observations if tc["type"] == "test_case"]
    # only the last test case observation, once we've finished shrinking it,
    # will include explain phase comments.
    #
    # Note that the output does *not* include `Explanation:` comments. See
    # https://github.com/HypothesisWorks/hypothesis/pull/4399#discussion_r2101559648
    expected = textwrap.dedent(
        r"""
        test_fails\(
            x=1,
            y=0,  # or any other generated value
        \)
    """
    ).strip()
    assert re.fullmatch(expected, test_cases[-1]["representation"])


def test_failure_includes_notes():
    @given(st.data())
    @settings(database=None)
    def test_fails_with_note(data):
        note("not included 1")
        data.draw(st.booleans())
        note("not included 2")
        raise AssertionError

    with (
        capture_observations() as observations,
        pytest.raises(AssertionError),
    ):
        test_fails_with_note()

    expected = textwrap.dedent(
        """
        test_fails_with_note(
            data=data(...),
        )
        Draw 1: False
    """
    ).strip()
    test_cases = [tc for tc in observations if tc["type"] == "test_case"]
    assert test_cases[-1]["representation"] == expected


def test_normal_representation_includes_draws():
    @given(st.data())
    def f(data):
        b1 = data.draw(st.booleans())
        note("not included")
        b2 = data.draw(st.booleans(), label="second")
        assume(b1 and b2)

    with capture_observations() as observations:
        f()

    crosshair = settings._current_profile == "crosshair"
    expected = textwrap.dedent(
        f"""
        f(
            data={'<symbolic>' if crosshair else 'data(...)'},
        )
        Draw 1: True
        Draw 2 (second): True
    """
    ).strip()
    test_cases = [
        tc
        for tc in observations
        if tc["type"] == "test_case" and tc["status"] == "passed"
    ]
    assert test_cases
    # TODO crosshair has a soundness bug with assume. remove branch when fixed
    # https://github.com/pschanely/hypothesis-crosshair/issues/34
    if not crosshair:
        assert {tc["representation"] for tc in test_cases} == {expected}


@xfail_on_crosshair(Why.other)
def test_capture_named_arguments():
    @given(named1=st.integers(), named2=st.floats(), data=st.data())
    def f(named1, named2, data):
        data.draw(st.booleans())

    with capture_observations() as observations:
        f()

    test_cases = [tc for tc in observations if tc["type"] == "test_case"]
    for test_case in test_cases:
        assert list(test_case["arguments"].keys()) == [
            "named1",
            "named2",
            "data",
            "Draw 1",
        ], test_case


def test_assume_has_status_reason():
    @given(st.booleans())
    def f(b):
        assume(b)

    with capture_observations() as ls:
        f()

    gave_ups = [t for t in ls if t["type"] == "test_case" and t["status"] == "gave_up"]
    for gave_up in gave_ups:
        assert gave_up["status_reason"].startswith("failed to satisfy assume() in f")


@settings(max_examples=20, stateful_step_count=5)
class UltraSimpleMachine(RuleBasedStateMachine):
    value = 0

    @rule()
    def inc(self):
        self.value += 1

    @rule()
    def dec(self):
        self.value -= 1

    @invariant()
    def limits(self):
        assert abs(self.value) <= 100


@xfail_on_crosshair(Why.other, strict=False)
def test_observability_captures_stateful_reprs():
    with capture_observations() as ls:
        run_state_machine_as_test(UltraSimpleMachine)

    for x in ls:
        if x["type"] != "test_case" or x["status"] == "gave_up":
            continue
        r = x["representation"]
        assert "state.limits()" in r
        assert "state.inc()" in r or "state.dec()" in r  # or both

        t = x["timing"]
        assert "execute:invariant:limits" in t
        has_inc = "generate:rule:inc" in t and "execute:rule:inc" in t
        has_dec = "generate:rule:dec" in t and "execute:rule:dec" in t
        assert has_inc or has_dec
