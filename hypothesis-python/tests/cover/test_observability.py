# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import base64
import json
import math
import textwrap
from contextlib import nullcontext

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
from hypothesis.internal.conjecture.choice import ChoiceNode, choices_key
from hypothesis.internal.coverage import IN_COVERAGE_TESTS
from hypothesis.internal.floats import SIGNALING_NAN, float_to_int, int_to_float
from hypothesis.internal.intervalsets import IntervalSet
from hypothesis.internal.observability import choices_to_json, nodes_to_json
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    rule,
    run_state_machine_as_test,
)

from tests.common.utils import Why, capture_observations, xfail_on_crosshair
from tests.conjecture.common import choices, integer_constr, nodes


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

    infos = [t for t in ls if t.type == "info"]
    assert len(infos) == 2
    assert {t.title for t in infos} == {"Hypothesis Statistics"}

    testcases = [t for t in ls if t.type == "test_case"]
    assert len(testcases) > 50
    assert {t.property for t in testcases} == {do_it_all.__name__}
    assert len({t.run_start for t in testcases}) == 2
    assert {t.status for t in testcases} == {"gave_up", "passed", "failed"}
    for t in testcases:
        if t.status != "gave_up":
            assert t.timing
            assert ("interactive" in t.arguments) == (
                "generate:interactive" in t.timing
            )


@xfail_on_crosshair(Why.other)
def test_capture_unnamed_arguments():
    @given(st.integers(), st.floats(), st.data())
    def f(v1, v2, data):
        data.draw(st.booleans())

    with capture_observations() as observations:
        f()

    test_cases = [tc for tc in observations if tc.type == "test_case"]
    for test_case in test_cases:
        assert list(test_case.arguments.keys()) == [
            "v1",
            "v2",
            "data",
            "Draw 1",
        ], test_case


@pytest.mark.skipif(
    PYPY or IN_COVERAGE_TESTS, reason="coverage requires sys.settrace pre-3.12"
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

    test_cases = [tc for tc in observations if tc.type == "test_case"]
    # only the last test case observation, once we've finished shrinking it,
    # will include explain phase comments.
    #
    # Note that the output does *not* include `Explanation:` comments. See
    # https://github.com/HypothesisWorks/hypothesis/pull/4399#discussion_r2101559648
    expected = textwrap.dedent(
        r"""
        test_fails(
            x=1,
            y=0,  # or any other generated value
        )
    """
    ).strip()
    assert test_cases[-1].representation == expected


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
    test_cases = [tc for tc in observations if tc.type == "test_case"]
    assert test_cases[-1].representation == expected


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
        tc for tc in observations if tc.type == "test_case" and tc.status == "passed"
    ]
    assert test_cases
    # TODO crosshair has a soundness bug with assume. remove branch when fixed
    # https://github.com/pschanely/hypothesis-crosshair/issues/34
    if not crosshair:
        assert {tc.representation for tc in test_cases} == {expected}


@xfail_on_crosshair(Why.other)
def test_capture_named_arguments():
    @given(named1=st.integers(), named2=st.floats(), data=st.data())
    def f(named1, named2, data):
        data.draw(st.booleans())

    with capture_observations() as observations:
        f()

    test_cases = [tc for tc in observations if tc.type == "test_case"]
    for test_case in test_cases:
        assert list(test_case.arguments.keys()) == [
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

    gave_ups = [t for t in ls if t.type == "test_case" and t.status == "gave_up"]
    for gave_up in gave_ups:
        assert gave_up.status_reason.startswith("failed to satisfy assume() in f")


@pytest.mark.skipif(
    PYPY or IN_COVERAGE_TESTS, reason="coverage requires sys.settrace pre-3.12"
)
def test_minimal_failing_observation():
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

    observation = [tc for tc in observations if tc.type == "test_case"][-1]
    expected_representation = textwrap.dedent(
        r"""
        test_fails(
            x=1,
            y=0,  # or any other generated value
        )
    """
    ).strip()

    assert observation.type == "test_case"
    assert observation.property == "test_fails"
    assert observation.status == "failed"
    assert "AssertionError" in observation.status_reason
    assert set(observation.timing.keys()) == {
        "execute:test",
        "overall:gc",
        "generate:x",
        "generate:y",
    }
    assert observation.coverage is None
    assert observation.features == {}
    assert observation.how_generated == "minimal failing example"
    assert "AssertionError" in observation.metadata.traceback
    assert "test_fails" in observation.metadata.traceback
    assert observation.metadata.reproduction_decorator.startswith("@reproduce_failure")
    assert observation.representation == expected_representation
    assert observation.arguments == {"x": 1, "y": 0}


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
        if x.type != "test_case" or x.status == "gave_up":
            continue
        r = x.representation
        assert "state.limits()" in r
        assert "state.inc()" in r or "state.dec()" in r  # or both

        t = x.timing
        assert "execute:invariant:limits" in t
        has_inc = "generate:rule:inc" in t and "execute:rule:inc" in t
        has_dec = "generate:rule:dec" in t and "execute:rule:dec" in t
        assert has_inc or has_dec


# BytestringProvider.draw_boolean divides [0, 127] as False and [128, 255]
# as True
@pytest.mark.parametrize(
    "buffer, expected_status",
    [
        # Status.OVERRUN
        (b"", "gave_up"),
        # Status.INVALID
        (b"\x00" + bytes([255]), "gave_up"),
        # Status.VALID
        (b"\x00\x00", "passed"),
        # Status.INTERESTING
        (bytes([255]) + b"\x00", "failed"),
    ],
)
def test_fuzz_one_input_status(buffer, expected_status):
    @given(st.booleans(), st.booleans())
    def test_fails(should_fail, should_fail_assume):
        if should_fail:
            raise AssertionError
        if should_fail_assume:
            assume(False)

    with (
        capture_observations() as ls,
        pytest.raises(AssertionError) if expected_status == "failed" else nullcontext(),
    ):
        test_fails.hypothesis.fuzz_one_input(buffer)
    assert len(ls) == 1
    assert ls[0].status == expected_status
    assert ls[0].how_generated == "fuzz_one_input"


def _decode_choice(value):
    if isinstance(value, list):
        if value[0] == "integer":
            # large integers get cast to string, stored as ["integer", str(value)]
            assert isinstance(value[1], str)
            return int(value[1])
        elif value[0] == "bytes":
            assert isinstance(value[1], str)
            return base64.b64decode(value[1])
        elif value[0] == "float":
            assert isinstance(value[1], int)
            choice = int_to_float(value[1])
            assert math.isnan(choice)
            return choice
        else:
            return value[1]

    return value


def _decode_choices(data):
    return [_decode_choice(value) for value in data]


def _decode_nodes(data):
    return [
        ChoiceNode(
            type=node["type"],
            value=_decode_choice(node["value"]),
            constraints=_decode_constraints(node["type"], node["constraints"]),
            was_forced=node["was_forced"],
        )
        for node in data
    ]


def _decode_constraints(choice_type, data):
    if choice_type == "integer":
        return {
            "min_value": _decode_choice(data["min_value"]),
            "max_value": _decode_choice(data["max_value"]),
            "weights": (
                None
                if data["weights"] is None
                else {_decode_choice(k): v for k, v in data["weights"]}
            ),
            "shrink_towards": _decode_choice(data["shrink_towards"]),
        }
    elif choice_type == "float":
        return {
            "min_value": _decode_choice(data["min_value"]),
            "max_value": _decode_choice(data["max_value"]),
            "allow_nan": data["allow_nan"],
            "smallest_nonzero_magnitude": data["smallest_nonzero_magnitude"],
        }
    elif choice_type == "string":
        return {
            "intervals": IntervalSet(tuple(data["intervals"])),
            "min_size": _decode_choice(data["min_size"]),
            "max_size": _decode_choice(data["max_size"]),
        }
    elif choice_type == "bytes":
        return {
            "min_size": _decode_choice(data["min_size"]),
            "max_size": _decode_choice(data["max_size"]),
        }
    elif choice_type == "boolean":
        return {"p": data["p"]}
    else:
        raise ValueError(f"unknown choice type {choice_type}")


@example([0.0])
@example([-0.0])
@example([SIGNALING_NAN])
@example([math.nan])
@example([math.inf])
@example([-math.inf])
@given(st.lists(choices()))
def test_choices_json_roundtrips(choices):
    choices2 = _decode_choices(json.loads(json.dumps(choices_to_json(choices))))
    assert choices_key(choices) == choices_key(choices2)


@given(st.lists(nodes()))
def test_nodes_json_roundtrips(nodes):
    nodes2 = _decode_nodes(json.loads(json.dumps(nodes_to_json(nodes))))
    assert nodes == nodes2


@pytest.mark.parametrize(
    "choice, expected",
    [
        (math.nan, ["float", float_to_int(math.nan)]),
        (SIGNALING_NAN, ["float", float_to_int(SIGNALING_NAN)]),
        (1, 1),
        (-1, -1),
        (2**63 + 1, ["integer", str(2**63 + 1)]),
        (-(2**63 + 1), ["integer", str(-(2**63 + 1))]),
        (1.0, 1.0),
        (-0.0, -0.0),
        (0.0, 0.0),
        (True, True),
        (False, False),
        (b"a", ["bytes", "YQ=="]),
    ],
)
def test_choices_to_json_explicit(choice, expected):
    assert choices_to_json([choice]) == [expected]


@pytest.mark.parametrize(
    "choice_node, expected",
    [
        (
            ChoiceNode(
                type="integer",
                value=2**63 + 1,
                constraints=integer_constr(),
                was_forced=False,
            ),
            {
                "type": "integer",
                "value": ["integer", str(2**63 + 1)],
                "constraints": integer_constr(),
                "was_forced": False,
            },
        ),
    ],
)
def test_choice_nodes_to_json_explicit(choice_node, expected):
    assert nodes_to_json([choice_node]) == [expected]
