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
import hypothesis.strategies as s
from hypothesis import Settings, find, assume
from hypothesis.errors import NoSuchExample, Unsatisfiable
from hypothesis.internal.tracker import Tracker


def test_stops_after_max_examples_if_satisfying():
    tracker = Tracker()

    def track(x):
        tracker.track(x)
        return False

    max_examples = 100

    with pytest.raises(NoSuchExample):
        find(
            s.integers(0, 10000),
            track, settings=Settings(max_examples=max_examples))

    assert len(tracker) == max_examples


def test_stops_after_max_iterations_if_not_satisfying():
    tracker = Tracker()

    def track(x):
        tracker.track(x)
        assume(False)

    max_examples = 100
    max_iterations = 200

    with pytest.raises(Unsatisfiable):
        find(
            s.integers(0, 10000),
            track, settings=Settings(
                max_examples=max_examples, max_iterations=max_iterations))

    assert len(tracker) == max_iterations
