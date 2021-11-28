# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

from fractions import Fraction

from hypothesis import assume, example, given, strategies as st, target
from hypothesis.internal.compat import int_to_bytes
from hypothesis.internal.conjecture import utils as cu
from hypothesis.internal.conjecture.data import ConjectureData, StopTest
from hypothesis.internal.conjecture.engine import BUFFER_SIZE


def test_gives_the_correct_probabilities():
    weights = [Fraction(1), Fraction(9)]
    total = sum(weights)
    probabilities = [w / total for w in weights]

    sampler = cu.Sampler(probabilities)

    assert cu.Sampler(weights).table == sampler.table

    counts = [0] * len(weights)

    i = 0
    while i < 2 ** 16:
        data = ConjectureData.for_buffer(int_to_bytes(i, 2))
        try:
            c = sampler.sample(data)
            counts[c] += 1
            assert probabilities[c] >= Fraction(counts[c], 2 ** 16)
        except StopTest:
            pass
        if 1 in data.forced_indices:
            i += 256
        else:
            i += 1


# BUFFER_SIZE divided by (2bytes coin + 1byte element) gives the
# maximum number of elements that we would ever be able to generate.
@given(st.floats(0, BUFFER_SIZE // 3), st.integers(0, BUFFER_SIZE // 3))
def test_p_continue(average_size, max_size):
    assume(average_size <= max_size)
    p = cu._calc_p_continue(average_size, max_size)
    assert 0 <= target(p, label="p") <= 1
    abs_err = abs(average_size - cu._p_continue_to_avg(p, max_size))
    assert target(abs_err, label="abs_err") < 0.01


@example(1.1, 10)
@given(st.floats(0, 1), st.integers(0, BUFFER_SIZE // 3))
def test_p_continue_to_average(p_continue, max_size):
    average = cu._p_continue_to_avg(p_continue, max_size)
    assert 0 <= average <= max_size
