# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import HealthCheck, assume, given, settings
from hypothesis.internal.conjecture import utils as cu
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.strategies import integers


@settings(database=None, suppress_health_check=[HealthCheck.filter_too_much])
@given(integers(0, 100), integers(0, 100), integers(0, 100))
def test_forced_many(min_size, max_size, forced):
    assume(min_size <= forced <= max_size)

    many = cu.many(
        ConjectureData.for_buffer([0] * 500),
        min_size=min_size,
        average_size=(min_size + max_size) / 2,
        max_size=max_size,
        forced=forced,
    )
    for _ in range(forced):
        assert many.more()

    assert not many.more()


def test_biased_coin_can_be_forced():
    data = ConjectureData.for_buffer([0])
    assert data.draw_boolean(0.5, forced=True)

    data = ConjectureData.for_buffer([1])
    assert not data.draw_boolean(0.5, forced=False)
