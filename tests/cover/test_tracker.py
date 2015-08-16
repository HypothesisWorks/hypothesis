# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import pytest
from hypothesis.internal.tracker import Tracker


class Foo(object):

    def __trackas__(self):
        return 1


def test_tracking_custom():
    t = Tracker()
    assert t.track(Foo()) == 1
    assert t.track(Foo()) == 2


def test_tracking_classes_of_custom():
    t = Tracker()
    assert t.track(Foo) == 1
    assert t.track(Foo) == 2


def test_track_ints():
    t = Tracker()
    assert t.track(1) == 1
    assert t.track(1) == 2


def test_track_lists():
    t = Tracker()
    assert t.track([1]) == 1
    assert t.track([1]) == 2


def test_track_iterables():
    t = Tracker()
    assert t.track(iter([1])) == 1
    assert t.track(iter([1])) == 2


def test_track_dict():
    t = Tracker()
    assert t.track({1: 2}) == 1
    assert t.track({1: 3}) == 1


def test_nested_unhashables():
    t = Tracker()
    x = {u'foo': [1, 2, set((3, 4, 5, 6))], u'bar': 10}
    assert t.track(x) == 1
    assert t.track(x) == 2


def test_track_nan():
    t = Tracker()
    assert t.track(float(u'nan')) == 1
    assert t.track(float(u'nan')) == 2


def test_track_complex_with_nan():
    t = Tracker()
    nan = float(u'nan')
    assert t.track(complex(nan, 2)) == 1
    assert t.track(complex(nan, 2)) == 2
    assert t.track(complex(0, nan)) == 1
    assert t.track(complex(0, nan)) == 2
    assert t.track(complex(nan, nan)) == 1
    assert t.track(complex(nan, nan)) == 2


class Hello(object):

    def __repr__(self):
        return u'hello world'


def test_includes_repr_in_marshal_error():
    with pytest.raises(ValueError) as e:
        Tracker().track(Hello())
    assert u'hello world' in e.value.args[0]
