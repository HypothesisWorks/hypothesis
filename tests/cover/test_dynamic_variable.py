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

from hypothesis.utils.dynamicvariables import DynamicVariable


def test_can_assign():
    d = DynamicVariable(1)
    assert d.value == 1
    with d.with_value(2):
        assert d.value == 2
    assert d.value == 1


def test_can_nest():
    d = DynamicVariable(1)
    with d.with_value(2):
        assert d.value == 2
        with d.with_value(3):
            assert d.value == 3
        assert d.value == 2
    assert d.value == 1
