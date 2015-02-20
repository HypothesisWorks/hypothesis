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
from hypothesis.internal.extmethod import ExtMethod


def test_will_use_tightest_class():
    f = ExtMethod()

    @f.extend(object)
    def foo(x):
        return 0

    @f.extend(int)
    def bar(x):
        return 1

    assert f(object()) == 0
    assert f('') == 0
    assert f(10) == 1


def test_will_error_on_missing():
    f = ExtMethod()
    with pytest.raises(NotImplementedError):
        f(1)
