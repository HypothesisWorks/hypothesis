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
from hypothesis import Verifier, given


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
    (has_one_arg, given()),
    (has_one_arg, given(int)),
    (has_one_arg, given(hello=int)),
    (has_two_args, given()),
    (has_two_args, given(int)),
    (has_two_args, given(int, bool)),
    (has_a_default, given(int, int)),
    (has_a_default, given(int, int, int)),
]


@pytest.mark.parametrize(('f', 'g'), basic_test_cases)
def test_argspec_lines_up(f, g):
    af = inspect.getargspec(f)
    ag = inspect.getargspec(g(f))
    assert af.args == ag.args
    assert af.keywords == ag.keywords
    assert af.varargs == ag.varargs


def test_errors_on_unwanted_kwargs():
    with pytest.raises(TypeError):
        @given(hello=int, world=int)
        def greet(world):
            pass


def test_errors_on_too_many_positional_args():
    with pytest.raises(TypeError):
        @given(int, int, int)
        def foo(x, y):
            pass


def test_errors_on_any_varargs():
    with pytest.raises(TypeError):
        @given(int)
        def oops(*args):
            pass


def test_converts_provided_kwargs_into_args():
    @given(hello=int, world=int)
    def greet(**kwargs):
        pass

    assert inspect.getargspec(greet).args == ['hello', 'world']


def test_does_not_falsify_if_all_args_given():
    verifier = Verifier()
    verifier.falsify = None

    @given(int, int, verifier=verifier)
    def foo(x, y):
        pass

    foo(1, 2)
