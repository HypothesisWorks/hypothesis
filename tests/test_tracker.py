# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis.internal.tracker import Tracker


def test_track_ints():
    t = Tracker()
    assert t.track(1) == 1
    assert t.track(1) == 2


def test_track_lists():
    t = Tracker()
    assert t.track([1]) == 1
    assert t.track([1]) == 2


def test_nested_unhashables():
    t = Tracker()
    x = {'foo': [1, 2, {3, 4, 5, 6}], 'bar': 10}
    assert t.track(x) == 1
    assert t.track(x) == 2


def test_track_nan():
    t = Tracker()
    assert t.track(float('nan')) == 1
    assert t.track(float('nan')) == 2


def test_track_complex_with_nan():
    t = Tracker()
    nan = float('nan')
    assert t.track(complex(nan, 2)) == 1
    assert t.track(complex(nan, 2)) == 2
    assert t.track(complex(0, nan)) == 1
    assert t.track(complex(0, nan)) == 2
    assert t.track(complex(nan, nan)) == 1
    assert t.track(complex(nan, nan)) == 2
