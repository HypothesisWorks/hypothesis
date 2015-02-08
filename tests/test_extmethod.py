# coding=utf-8

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals

# END HEADER
from hypothesis.internal.extmethod import ExtMethod
import pytest


def test_will_use_tightest_class():
    f = ExtMethod()

    @f.extend(object)
    def foo():
        return 0

    @f.extend(int)
    def bar():
        return 1

    assert f(object) == 0
    assert f(str) == 0
    assert f(int) == 1


def test_will_error_on_missing():
    f = ExtMethod()
    with pytest.raises(NotImplementedError):
        f(int)
