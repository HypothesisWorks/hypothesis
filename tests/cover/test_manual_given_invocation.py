# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import pytest

from hypothesis import given, Settings
from hypothesis.strategies import booleans, integers
from hypothesis.internal.compat import getargspec


def has_one_arg(hello):
    pass


def has_two_args(hello, world):
    pass


def has_a_default(x, y, z=1):
    pass


def has_varargs(*args):
    pass


def has_kwargs(**kwargs):
    pass

basic_test_cases = [
    (has_one_arg, given(integers())),
    (has_one_arg, given(hello=integers())),
    (has_two_args, given(integers())),
    (has_two_args, given(integers(), booleans())),
    (has_a_default, given(integers(), integers())),
    (has_a_default, given(integers(), integers(), integers())),
]


@pytest.mark.parametrize((u'f', u'g'), basic_test_cases)
def test_argspec_lines_up(f, g):
    af = getargspec(f)
    ag = getargspec(g(f))
    assert af.args == ag.args
    assert af.keywords == ag.keywords
    assert af.varargs == ag.varargs


def test_does_not_convert_unknown_kwargs_into_args():
    @given(hello=int, world=int)
    def greet(hello, **kwargs):
        pass

    assert getargspec(greet).args == [u'hello']


def test_provided_kwargs_are_defaults():
    @given(hello=booleans(), world=booleans(), settings=Settings(
        strict=False
    ))
    def greet(hello, **kwargs):
        assert hello == u'salve'
        assert kwargs == {u'world': u'mundi'}

    greet(u'salve', world=u'mundi')
