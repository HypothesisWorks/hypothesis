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

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
from hypothesis import given
from hypothesis.errors import InvalidArgument
from hypothesis.strategies import floats, integers


def test_errors_when_given_varargs():
    with pytest.raises(InvalidArgument) as e:
        @given(integers())
        def has_varargs(*args):
            pass
    assert 'varargs' in e.value.args[0]


def test_bare_given_errors():
    with pytest.raises(InvalidArgument):
        given()


def test_errors_on_unwanted_kwargs():
    with pytest.raises(InvalidArgument):
        @given(hello=int, world=int)
        def greet(world):
            pass


def test_errors_on_too_many_positional_args():
    with pytest.raises(InvalidArgument):
        @given(integers(), int, int)
        def foo(x, y):
            pass


def test_errors_on_any_varargs():
    with pytest.raises(InvalidArgument):
        @given(integers())
        def oops(*args):
            pass


def test_cannot_put_kwargs_in_the_middle():
    with pytest.raises(InvalidArgument):
        @given(y=int)
        def foo(x, y, z):
            pass


def test_float_ranges():
    with pytest.raises(InvalidArgument):
        floats(float('nan'), 0)
    with pytest.raises(InvalidArgument):
        floats(1, -1)
