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

import pytest

from hypothesis import find, Settings
from tests.common import standard_types
from hypothesis.errors import NoSuchExample
from hypothesis.strategies import lists
from hypothesis.utils.show import show


@pytest.mark.parametrize(
    u'spec', standard_types, ids=list(map(show, standard_types)))
def test_can_collectively_minimize(spec):
    """This should generally exercise strategies' strictly_simpler heuristic by
    putting us in a state where example cloning is required to get to the
    answer fast enough."""

    if spec.template_upper_bound < 2:
        return
    n = 10

    def distinct_reprs(x):
        result = set()
        for t in x:
            result.add(repr(t))
            if len(result) >= 2:
                return True
        return False

    try:
        xs = find(
            lists(spec, min_size=n, max_size=n),
            distinct_reprs,
            settings=Settings(
                timeout=3.0, average_list_length=3, max_examples=2000))
        assert len(xs) == n
        assert 2 <= len(set((map(repr, xs)))) <= 3
    except NoSuchExample:
        pass
