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
