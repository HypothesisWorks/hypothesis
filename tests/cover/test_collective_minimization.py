# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import Settings, find
from hypothesis.specifiers import integers_from, floats_in_range, \
    integers_in_range
from hypothesis.internal.compat import text_type, binary_type


@pytest.mark.parametrize('spec', [
    int, integers_from(3), integers_in_range(-2 ** 32, 2 ** 64),
    float, floats_in_range(-2.0, 3.0),
    text_type, binary_type,
    bool,
    (bool, bool),
    frozenset({int}),
    complex,
    Fraction,
    Decimal,
    [[bool]],
])
def test_can_collectively_minimize(spec):
    """This should generally exercise strategies' strictly_simpler heuristic by
    putting us in a state where example cloning is required to get to the
    answer fast enough."""

    xs = find(
        [spec],
        lambda x: len(x) >= 10 and len(set((map(repr, x)))) >= 2,
        settings=Settings(timeout=1.0, average_list_length=5))
    assert len(xs) == 10
    assert len(set((map(repr, xs)))) == 2
