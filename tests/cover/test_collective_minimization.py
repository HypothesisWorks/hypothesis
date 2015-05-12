# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
from hypothesis import Settings, find
from tests.common import standard_types
from hypothesis.strategies import lists
from hypothesis.utils.show import show


@pytest.mark.parametrize(
    'spec', standard_types, ids=list(map(show, standard_types)))
def test_can_collectively_minimize(spec):
    """This should generally exercise strategies' strictly_simpler heuristic by
    putting us in a state where example cloning is required to get to the
    answer fast enough."""

    if spec.template_upper_bound < 2:
        return

    def distinct_reprs(x):
        result = set()
        for t in x:
            result.add(repr(t))
            if len(result) >= 2:
                return True
        return False

    xs = find(
        lists(spec, min_size=20, max_size=20),
        distinct_reprs,
        settings=Settings(timeout=2.0, average_list_length=3))
    assert len(xs) == 20
    assert len(set((map(repr, xs)))) == 2
