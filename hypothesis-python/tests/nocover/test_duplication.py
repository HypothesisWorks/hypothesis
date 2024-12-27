# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from collections import Counter

import pytest

from hypothesis import given, settings
from hypothesis.strategies._internal import SearchStrategy


class Blocks(SearchStrategy):
    def __init__(self, n):
        self.n = n

    def do_draw(self, data):
        return data.draw_bytes(self.n, self.n)


@pytest.mark.parametrize("n", range(1, 5))
def test_does_not_duplicate_blocks(n):
    counts = Counter()

    @given(Blocks(n))
    @settings(database=None)
    def test(b):
        counts[b] += 1

    test()
    assert set(counts.values()) == {1}


@pytest.mark.parametrize("n", range(1, 5))
def test_mostly_does_not_duplicate_blocks_even_when_failing(n):
    counts = Counter()

    @settings(database=None)
    @given(Blocks(n))
    def test(b):
        counts[b] += 1
        if len(counts) > 3:
            raise ValueError

    try:
        test()
    except ValueError:
        pass
    # There are two circumstances in which a duplicate is allowed: We replay
    # the failing test once to check for flakiness, and then we replay the
    # fully minimized failing test at the end to display the error. The
    # complication comes from the fact that these may or may not be the same
    # test case, so we can see either two test cases each run twice or one
    # test case which has been run three times.
    assert set(counts.values()) in ({1, 2}, {1, 3})
    assert len([k for k, v in counts.items() if v > 1]) <= 2
