# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import hashlib
from random import Random

import pytest
import hypothesis.strategies as s
from hypothesis.internal.compat import hrange
from hypothesis.utils.size import clamp

finite = [
    s.booleans(), s.sets(s.booleans()), s.integers(-10, 10),
    s.integers(0, 10) | s.integers(0, 1),
    s.tuples(s.booleans(), s.booleans()),
    s.frozensets(s.booleans()),
    s.sets(s.integers(0, 3)),
]


@pytest.mark.parametrize('strat', finite, ids=list(map(repr, finite)))
def test_covers_entire_finite_space(strat):
    assert strat.template_upper_bound <= 100

    random = Random(hashlib.md5(
        (repr(strat) + ':test_covers_entire_finite_space').encode('utf-8')
    ).digest())

    s = set()
    for _ in hrange(1000):
        s.add(strat.draw_and_produce(random))

    assert len(s) == strat.template_upper_bound


def test_large_enough_sets_are_infinite():
    assert s.sets(s.integers(0, 30)).template_upper_bound == float('inf')
    assert s.sets(s.integers(0, 100)).template_upper_bound == float('inf')


def test_clamp():
    assert clamp(None, 1, None) == 1
    assert clamp(None, 10, 1) == 1
    assert clamp(1, 0, 1) == 1
    assert clamp(1, 0, None) == 1
