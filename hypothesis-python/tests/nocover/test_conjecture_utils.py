# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys
from collections import Counter

from hypothesis import assume, example, given, settings, strategies as st, target
from hypothesis.internal.conjecture import utils as cu
from hypothesis.internal.conjecture.engine import BUFFER_SIZE

from tests.conjecture.common import fresh_data, integer_weights


@given(integer_weights(), st.randoms(use_true_random=True))
@settings(max_examples=3)
def test_sampler_matches_distribution(weights, random):
    # if we randomly sample from Sampler(weights), the resulting distribution
    # should match the weights (to some tolerance).

    weights = weights.values()
    sampler = cu.Sampler(weights)
    counter = Counter()
    for _ in range(10_000):
        cd = fresh_data(random=random)
        n = sampler.sample(cd)
        counter[n] += 1

    # if we ever pull in scipy to our test suite, we should do a chi squared
    # test here instead.
    expected = [w / sum(weights) for w in weights]
    actual = [counter[i] / counter.total() for i in range(len(weights))]
    for p1, p2 in zip(expected, actual):
        assert abs(p1 - p2) < 0.05, (expected, actual)


@example(0, 1)
@example(0, float("inf"))
@example(cu.SMALLEST_POSITIVE_FLOAT, 2 * cu.SMALLEST_POSITIVE_FLOAT)
@example(cu.SMALLEST_POSITIVE_FLOAT, 1)
@example(cu.SMALLEST_POSITIVE_FLOAT, float("inf"))
@example(sys.float_info.min, 1)
@example(sys.float_info.min, float("inf"))
@example(10, 10)
@example(10, float("inf"))
# BUFFER_SIZE divided by (2bytes coin + 0byte element) gives the
# maximum number of elements that we would ever be able to generate.
@given(st.floats(0, BUFFER_SIZE // 2), st.integers(0, BUFFER_SIZE // 2))
def test_p_continue(average_size, max_size):
    assume(average_size <= max_size)
    p = cu._calc_p_continue(average_size, max_size)
    assert 0 <= target(p, label="p") <= 1
    assert 0 < target(p, label="-p") or average_size < 1e-5
    abs_err = abs(average_size - cu._p_continue_to_avg(p, max_size))
    assert target(abs_err, label="abs_err") < 0.01


@example(1.1, 10)
@given(st.floats(0, 1), st.integers(0, BUFFER_SIZE // 2))
def test_p_continue_to_average(p_continue, max_size):
    average = cu._p_continue_to_avg(p_continue, max_size)
    assert 0 <= average <= max_size
