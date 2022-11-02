# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from tests.common.debug import find_any

from hypothesis import given, settings
from hypothesis.strategies import floats, integers, sets


def test_can_draw_sets_of_hard_to_find_elements():
    rarebool = floats(0, 1).map(lambda x: x <= 0.05)
    find_any(sets(rarebool, min_size=2), settings=settings(deadline=None))


@given(sets(integers(), max_size=0))
def test_empty_sets(x):
    assert x == set()


@given(sets(integers(), max_size=2))
def test_bounded_size_sets(x):
    assert len(x) <= 2
