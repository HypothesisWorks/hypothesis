# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import hashlib
from random import Random

import pytest

import hypothesis.strategies as s
from hypothesis.utils.size import clamp
from hypothesis.internal.compat import hrange

finite = [
    s.booleans(), s.integers(-10, 10),
    s.integers(0, 10) | s.integers(0, 1),
    s.tuples(s.booleans(), s.booleans()),
]


@pytest.mark.parametrize(u'strat', finite, ids=list(map(repr, finite)))
def test_covers_entire_finite_space(strat):
    assert strat.template_upper_bound <= 100

    random = Random(hashlib.md5(
        (repr(strat) + u':test_covers_entire_finite_space').encode(u'utf-8')
    ).digest())

    s = set()
    for _ in hrange(2000):
        s.add(strat.draw_and_produce(random))

    assert len(s) == strat.template_upper_bound


def test_clamp():
    assert clamp(None, 1, None) == 1
    assert clamp(None, 10, 1) == 1
    assert clamp(1, 0, 1) == 1
    assert clamp(1, 0, None) == 1
