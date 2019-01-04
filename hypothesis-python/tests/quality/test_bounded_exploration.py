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
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

from random import Random

import pytest

import hypothesis.strategies as st
from hypothesis import HealthCheck, settings, unlimited
from hypothesis.internal.compat import hrange
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.utils.conventions import not_set


@pytest.mark.parametrize(
    "strategy",
    [
        st.text(),
        st.floats(allow_nan=False),
        st.lists(st.integers(), unique=True).map(tuple),
    ],
)
@pytest.mark.parametrize("seed", [32910, 46074])
def test_reliably_enumerates_small_values(strategy, seed):
    random = Random(seed)

    used_values = set()
    for _ in hrange(10):

        def test_function(data):
            value = data.draw(strategy)
            data.output = value
            if value not in used_values:
                data.mark_interesting()

        def calc_target(data):
            return (data.buffer, data.output)

        target = not_set

        for _ in hrange(3):
            runner = ConjectureRunner(
                test_function,
                settings=settings(
                    suppress_health_check=HealthCheck.all(),
                    timeout=unlimited,
                    deadline=None,
                    database=None,
                ),
                random=random,
            )

            runner.run()

            data, = runner.interesting_examples.values()
            result = calc_target(data)
            if target is not_set:
                target = result
            else:
                assert target == result
        used_values.add(target[1])
