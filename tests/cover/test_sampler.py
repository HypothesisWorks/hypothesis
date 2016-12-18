# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

from __future__ import division, print_function, absolute_import

from random import Random

from hypothesis import strategies as st
from hypothesis import given
from hypothesis.internal.compat import hrange
from hypothesis.internal.sampler import VoseAliasSampler

weightings = st.lists(
    st.integers(0, 1000), min_size=1
).filter(any)


@given(weightings)
def test_sampler_can_be_instantiated_and_read(weights):
    r = Random(0)
    sampler = VoseAliasSampler(weights)

    n_samples = 1000

    vs = [sampler.sample(r) for v in hrange(n_samples)]
    for i in vs:
        assert 0 <= i < len(weights)
        assert weights[i] != 0

    calculated_weights = [0.0] * len(weights)
    for i, (alias, p) in enumerate(
        zip(sampler._alias, sampler._probabilities)
    ):
        calculated_weights[i] += p / len(weights)
        calculated_weights[alias] += (1 - p) / len(weights)
    assert 0.99 <= sum(calculated_weights) <= 1.01

    for i, w in enumerate(weights):
        w /= sum(weights)
        cw = calculated_weights[i]
        assert cw * 0.99 <= w <= 1.01 * cw
