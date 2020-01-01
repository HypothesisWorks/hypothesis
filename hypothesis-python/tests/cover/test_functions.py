# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

import pytest

from hypothesis import given
from hypothesis.errors import InvalidArgument, InvalidState
from hypothesis.internal.compat import getfullargspec
from hypothesis.strategies import booleans, functions


def func_a():
    pass


@given(functions(func_a, booleans()))
def test_functions_no_args(f):
    assert f.__name__ == "func_a"
    assert f is not func_a
    assert isinstance(f(), bool)


def func_b(a, b, c):
    pass


@given(functions(func_b, booleans()))
def test_functions_with_args(f):
    assert f.__name__ == "func_b"
    assert f is not func_b
    with pytest.raises(TypeError):
        f()
    assert isinstance(f(1, 2, 3), bool)


def func_c(**kwargs):
    pass


@given(functions(func_c, booleans()))
def test_functions_kw_args(f):
    assert f.__name__ == "func_c"
    assert f is not func_c
    with pytest.raises(TypeError):
        f(1, 2, 3)
    assert isinstance(f(a=1, b=2, c=3), bool)


@given(functions(lambda: None, booleans()))
def test_functions_argless_lambda(f):
    assert f.__name__ == "<lambda>"
    with pytest.raises(TypeError):
        f(1)
    assert isinstance(f(), bool)


@given(functions(lambda a: None, booleans()))
def test_functions_lambda_with_arg(f):
    assert f.__name__ == "<lambda>"
    with pytest.raises(TypeError):
        f()
    assert isinstance(f(1), bool)


@pytest.mark.parametrize("like,returns", [(None, booleans()), (lambda: None, None)])
def test_invalid_arguments(like, returns):
    with pytest.raises(InvalidArgument):
        functions(like, returns).example()


def test_functions_valid_within_given_invalid_outside():
    cache = [None]

    @given(functions())
    def t(f):
        assert f() is None
        cache[0] = f

    t()
    with pytest.raises(InvalidState):
        cache[0]()


def test_can_call_default_like_arg():
    # This test is somewhat silly, but coverage complains about the uncovered
    # branch for calling it otherwise and alternative workarounds are worse.
    like, returns = getfullargspec(functions).defaults
    assert like() is None
    assert returns.example() is None


def func(arg, *, kwonly_arg):
    pass


@given(functions(func))
def test_functions_strategy_with_kwonly_args(f):
    with pytest.raises(TypeError):
        f(1, 2)
    f(1, kwonly_arg=2)
    f(kwonly_arg=2, arg=1)
