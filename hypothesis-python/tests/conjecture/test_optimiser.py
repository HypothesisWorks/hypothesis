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

from hypothesis import assume, example, given, settings
from hypothesis.internal.conjecture.choice import ChoiceNode
from hypothesis.internal.conjecture.data import Status
from hypothesis.internal.conjecture.datatree import compute_max_children
from hypothesis.internal.conjecture.engine import ConjectureRunner, RunIsComplete
from hypothesis.internal.entropy import deterministic_PRNG
from hypothesis.internal.intervalsets import IntervalSet

from tests.conjecture.common import (
    TEST_SETTINGS,
    buffer_size_limit,
    integer_constr,
    nodes,
)


def test_optimises_to_maximum():
    with deterministic_PRNG():

        def test(data):
            data.target_observations["m"] = data.draw_integer(0, 2**8 - 1)

        runner = ConjectureRunner(test, settings=TEST_SETTINGS)
        runner.cached_test_function((0,))

        try:
            runner.optimise_targets()
        except RunIsComplete:
            pass

        assert runner.best_observed_targets["m"] == 255


def test_optimises_multiple_targets():
    with deterministic_PRNG():

        def test(data):
            n = data.draw_integer(0, 2**8 - 1)
            m = data.draw_integer(0, 2**8 - 1)
            if n + m > 256:
                data.mark_invalid()
            data.target_observations["m"] = m
            data.target_observations["n"] = n
            data.target_observations["m + n"] = m + n

        runner = ConjectureRunner(test, settings=TEST_SETTINGS)
        runner.cached_test_function((200, 0))
        runner.cached_test_function((0, 200))

        try:
            runner.optimise_targets()
        except RunIsComplete:
            pass

        assert runner.best_observed_targets["m"] == 255
        assert runner.best_observed_targets["n"] == 255
        assert runner.best_observed_targets["m + n"] == 256


def test_optimises_when_last_element_is_empty():
    with deterministic_PRNG():

        def test(data):
            data.target_observations["n"] = data.draw_integer(0, 2**8 - 1)
            data.start_span(label=1)
            data.stop_span()

        runner = ConjectureRunner(test, settings=TEST_SETTINGS)
        runner.cached_test_function((250,))

        try:
            runner.optimise_targets()
        except RunIsComplete:
            pass

        assert runner.best_observed_targets["n"] == 255


def test_can_optimise_last_with_following_empty():
    with deterministic_PRNG():

        def test(data):
            for _ in range(100):
                data.draw_integer(0, 3)
            data.target_observations[""] = data.draw_integer(0, 2**8 - 1)
            data.start_span(1)
            data.stop_span()

        runner = ConjectureRunner(
            test, settings=settings(TEST_SETTINGS, max_examples=100)
        )
        runner.cached_test_function((0,) * 101)

        with pytest.raises(RunIsComplete):
            runner.optimise_targets()
        assert runner.best_observed_targets[""] == 255


@pytest.mark.parametrize("lower, upper", [(0, 1000), (13, 100), (1000, 2**16 - 1)])
@pytest.mark.parametrize("score_up", [False, True])
def test_can_find_endpoints_of_a_range(lower, upper, score_up):
    with deterministic_PRNG():

        def test(data):
            n = data.draw_integer(0, 2**16 - 1)
            if n < lower or n > upper:
                data.mark_invalid()
            if not score_up:
                n = -n
            data.target_observations["n"] = n

        runner = ConjectureRunner(
            test, settings=settings(TEST_SETTINGS, max_examples=1000)
        )
        runner.cached_test_function(((lower + upper) // 2,))

        try:
            runner.optimise_targets()
        except RunIsComplete:
            pass
        if score_up:
            assert runner.best_observed_targets["n"] == upper
        else:
            assert runner.best_observed_targets["n"] == -lower


def test_targeting_can_drive_length_very_high():
    with deterministic_PRNG():

        def test(data):
            count = 0
            while data.draw_boolean(0.25):
                count += 1
            data.target_observations[""] = min(count, 100)

        runner = ConjectureRunner(test, settings=TEST_SETTINGS)
        # extend here to ensure we get a valid (non-overrun) test case. The
        # outcome of the test case doesn't really matter as long as we have
        # something for the runner to optimize.
        runner.cached_test_function([], extend=50)

        try:
            runner.optimise_targets()
        except RunIsComplete:
            pass

        assert runner.best_observed_targets[""] == 100


def test_optimiser_when_test_grows_buffer_to_invalid():
    with deterministic_PRNG():

        def test(data):
            m = data.draw_integer(0, 2**8 - 1)
            data.target_observations["m"] = m
            if m > 100:
                data.draw_integer(0, 2**16 - 1)
                data.mark_invalid()

        runner = ConjectureRunner(test, settings=TEST_SETTINGS)
        runner.cached_test_function((0,) * 10)

        try:
            runner.optimise_targets()
        except RunIsComplete:
            pass

        assert runner.best_observed_targets["m"] == 100


def test_can_patch_up_examples():
    with deterministic_PRNG():

        def test(data):
            data.start_span(42)
            m = data.draw_integer(0, 2**6 - 1)
            data.target_observations["m"] = m
            for _ in range(m):
                data.draw_boolean()
            data.stop_span()
            for i in range(4):
                if i != data.draw_integer(0, 2**8 - 1):
                    data.mark_invalid()

        runner = ConjectureRunner(test, settings=TEST_SETTINGS)
        d = runner.cached_test_function((0, 0, 1, 2, 3, 4))
        assert d.status == Status.VALID

        try:
            runner.optimise_targets()
        except RunIsComplete:
            pass

        assert runner.best_observed_targets["m"] == 63


def test_optimiser_when_test_grows_buffer_to_overflow():
    with deterministic_PRNG():
        with buffer_size_limit(2):

            def test(data):
                m = data.draw_integer(0, 2**8 - 1)
                data.target_observations["m"] = m
                if m > 100:
                    data.draw_integer(0, 2**64 - 1)
                    data.mark_invalid()

            runner = ConjectureRunner(test, settings=TEST_SETTINGS)
            runner.cached_test_function((0,) * 10)

            try:
                runner.optimise_targets()
            except RunIsComplete:
                pass

            assert runner.best_observed_targets["m"] == 100


@given(nodes())
@example(
    ChoiceNode(
        type="bytes",
        value=b"\xb1",
        constraints={"min_size": 1, "max_size": 1},
        was_forced=False,
    )
)
@example(
    ChoiceNode(
        type="string",
        value="aaaa",
        constraints={
            "min_size": 0,
            "max_size": 10,
            "intervals": IntervalSet.from_string("abcd"),
        },
        was_forced=False,
    )
)
@example(
    ChoiceNode(
        type="integer", value=1, constraints=integer_constr(0, 200), was_forced=False
    )
)
def test_optimising_all_nodes(node):
    assume(compute_max_children(node.type, node.constraints) > 50)
    size_function = {
        "integer": lambda n: n,
        "float": lambda f: f if math.isfinite(f) else 0,
        "string": lambda s: len(s),
        "bytes": lambda b: len(b),
        "boolean": lambda b: int(b),
    }
    with deterministic_PRNG():

        def test(data):
            v = getattr(data, f"draw_{node.type}")(**node.constraints)
            data.target_observations["v"] = size_function[node.type](v)

        runner = ConjectureRunner(
            test, settings=settings(TEST_SETTINGS, max_examples=50)
        )
        runner.cached_test_function([node.value])

        try:
            runner.optimise_targets()
        except RunIsComplete:
            pass
