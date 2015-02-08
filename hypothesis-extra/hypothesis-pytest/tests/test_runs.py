# coding=utf-8

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals

# END HEADER

from hypothesis import given
from functools import wraps
import pytest


def fails(f):
    @wraps(f)
    def inverted_test(*arguments, **kwargs):
        with pytest.raises(AssertionError):
            f(*arguments, **kwargs)
    return inverted_test


@given(int)
def test_ints_are_ints(x):
    pass


@fails
@given(int)
def test_ints_are_floats(x):
    assert isinstance(x, float)
