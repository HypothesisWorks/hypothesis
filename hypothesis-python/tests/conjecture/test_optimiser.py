# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import pytest

from hypothesis import settings
from hypothesis.internal.compat import hbytes, int_to_bytes
from hypothesis.internal.conjecture.engine import ConjectureRunner, RunIsComplete
from hypothesis.internal.entropy import deterministic_PRNG
from tests.conjecture.common import TEST_SETTINGS


def test_optimises_multiple_targets():
    with deterministic_PRNG():

        def test(data):
            n = data.draw_bits(8)
            m = data.draw_bits(8)
            if n + m > 256:
                data.mark_invalid()
            data.target_observations["m"] = m
            data.target_observations["n"] = n
            data.target_observations["m + n"] = m + n

        runner = ConjectureRunner(test, settings=TEST_SETTINGS)
        runner.cached_test_function([200, 0])
        runner.cached_test_function([0, 200])

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
            data.target_observations["n"] = data.draw_bits(8)
            data.start_example(1)
            data.stop_example(1)

        runner = ConjectureRunner(test, settings=TEST_SETTINGS)
        runner.cached_test_function([250])

        try:
            runner.optimise_targets()
        except RunIsComplete:
            pass

        assert runner.best_observed_targets["n"] == 255


def test_can_optimise_last_with_following_empty():
    with deterministic_PRNG():

        def test(data):
            for _ in range(100):
                data.draw_bits(2)
            data.target_observations[""] = data.draw_bits(8)
            data.start_example(1)
            data.stop_example()

        runner = ConjectureRunner(
            test, settings=settings(TEST_SETTINGS, max_examples=100)
        )
        runner.cached_test_function(hbytes(101))

        with pytest.raises(RunIsComplete):
            runner.optimise_targets()
        assert runner.best_observed_targets[""] == 255


@pytest.mark.parametrize("lower, upper", [(0, 1000), (13, 100), (1000, 2 ** 16 - 1)])
@pytest.mark.parametrize("score_up", [False, True])
def test_can_find_endpoints_of_a_range(lower, upper, score_up):
    with deterministic_PRNG():

        def test(data):
            n = data.draw_bits(16)
            if n < lower or n > upper:
                data.mark_invalid()
            if not score_up:
                n = -n
            data.target_observations["n"] = n

        runner = ConjectureRunner(
            test, settings=settings(TEST_SETTINGS, max_examples=1000)
        )
        runner.cached_test_function(int_to_bytes((lower + upper) // 2, 2))

        try:
            runner.optimise_targets()
        except RunIsComplete:
            pass
        if score_up:
            assert runner.best_observed_targets["n"] == upper
        else:
            assert runner.best_observed_targets["n"] == -lower
