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
from hypothesis.utils.extmethod import ExtMethod


def test_will_use_tightest_class():
    f = ExtMethod()

    @f.extend(object)
    def foo(x):
        return 0

    @f.extend(int)
    def bar(x):
        return 1

    assert f(object()) == 0
    assert f(u'') == 0
    assert f(10) == 1


def test_will_error_on_missing():
    f = ExtMethod()
    with pytest.raises(NotImplementedError):
        f(1)


def test_can_add_static():
    f = ExtMethod()

    @f.extend_static(object)
    def fs(x):
        return 1

    @f.extend_static(int)
    def fi(x):
        return 2

    assert f(object) == 1
    assert f(int) == 2
    assert f(str) == 1


def test_will_use_instance_if_no_static():
    f = ExtMethod()

    @f.extend(object)
    def foo(x):
        return x

    assert f(int) == int
