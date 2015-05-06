# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import inspect

import pytest
from hypothesis import given
from hypothesis.strategies import booleans, integers


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


@pytest.mark.parametrize(('f', 'g'), basic_test_cases)
def test_argspec_lines_up(f, g):
    af = inspect.getargspec(f)
    ag = inspect.getargspec(g(f))
    assert af.args == ag.args
    assert af.keywords == ag.keywords
    assert af.varargs == ag.varargs


def test_converts_provided_kwargs_into_args():
    @given(hello=int, world=int)
    def greet(**kwargs):
        pass

    assert inspect.getargspec(greet).args == ['hello', 'world']
