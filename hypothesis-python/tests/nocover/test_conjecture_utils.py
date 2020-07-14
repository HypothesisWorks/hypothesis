# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

from hypothesis.internal.compat import int_to_bytes
from hypothesis.internal.conjecture import utils as cu
from hypothesis.internal.conjecture.data import ConjectureData, StopTest


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
