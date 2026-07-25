# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from inspect import signature

import pytest

from hypothesis import Verbosity, assume, find, given, settings, strategies as st
from hypothesis.errors import InvalidArgument, InvalidState
from hypothesis.internal.reflection import nicerepr
from hypothesis.reporting import with_reporter
from hypothesis.strategies import booleans, functions, integers

from tests.common.debug import check_can_generate_examples
from tests.common.utils import capture_out


def func_a():
    pass


@given(functions(like=func_a, returns=booleans()))
def test_functions_no_args(f):
    assert f.__name__ == "func_a"
    assert f is not func_a
    assert isinstance(f(), bool)


def func_b(a, b, c):
    pass


@given(functions(like=func_b, returns=booleans()))
def test_functions_with_args(f):
    assert f.__name__ == "func_b"
    assert f is not func_b
    with pytest.raises(TypeError):
        f()
    assert isinstance(f(1, 2, 3), bool)


def func_c(**kwargs):
    pass


@given(functions(like=func_c, returns=booleans()))
def test_functions_kw_args(f):
    assert f.__name__ == "func_c"
    assert f is not func_c
    with pytest.raises(TypeError):
        f(1, 2, 3)
    assert isinstance(f(a=1, b=2, c=3), bool)


@given(functions(like=lambda: None, returns=booleans()))
def test_functions_argless_lambda(f):
    assert f.__name__ == "<lambda>"
    with pytest.raises(TypeError):
        f(1)
    assert isinstance(f(), bool)


@given(functions(like=lambda a: None, returns=booleans()))
def test_functions_lambda_with_arg(f):
    assert f.__name__ == "<lambda>"
    with pytest.raises(TypeError):
        f()
    assert isinstance(f(1), bool)


@pytest.mark.parametrize(
    "like,returns,pure",
    [
        (None, booleans(), False),
        (lambda: None, "not a strategy", True),
        (lambda: None, booleans(), None),
    ],
)
def test_invalid_arguments(like, returns, pure):
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(functions(like=like, returns=returns, pure=pure))


def func_returns_str() -> str:
    return "a string"


@given(functions(like=func_returns_str))
def test_functions_strategy_return_type_inference(f):
    result = f()
    assume(result != "a string")
    assert isinstance(result, str)


def test_functions_valid_within_given_invalid_outside():
    cache = None

    @given(functions())
    def t(f):
        nonlocal cache
        cache = f
        assert f() is None

    t()
    with pytest.raises(InvalidState):
        cache()


def test_can_call_default_like_arg():
    # This test is somewhat silly, but coverage complains about the uncovered
    # branch for calling it otherwise and alternative workarounds are worse.
    like, returns, pure = signature(functions).parameters.values()
    assert like.default() is None
    assert returns.default is ...
    assert pure.default is False


def func(arg, *, kwonly_arg):
    pass


@given(functions(like=func))
def test_functions_strategy_with_kwonly_args(f):
    with pytest.raises(TypeError):
        f(1, 2)
    f(1, kwonly_arg=2)
    f(kwonly_arg=2, arg=1)


def pure_func(arg1, arg2):
    pass


@given(
    f=functions(like=pure_func, returns=integers(), pure=True),
    arg1=integers(),
    arg2=integers(),
)
def test_functions_pure_with_same_args(f, arg1, arg2):
    # Same regardless of calling convention, unlike functools.lru_cache()
    expected = f(arg1, arg2)
    assert f(arg1, arg2) == expected
    assert f(arg1, arg2=arg2) == expected
    assert f(arg1=arg1, arg2=arg2) == expected
    assert f(arg2=arg2, arg1=arg1) == expected


@given(
    f=functions(like=pure_func, returns=integers(), pure=True),
    arg1=integers(),
    arg2=integers(),
)
def test_functions_pure_with_different_args(f, arg1, arg2):
    r1 = f(arg1, arg2)
    r2 = f(arg2, arg1)
    assume(r1 != r2)
    # If this is never true, the test will fail with Unsatisfiable


@given(
    f1=functions(like=pure_func, returns=integers(), pure=True),
    f2=functions(like=pure_func, returns=integers(), pure=True),
)
def test_functions_pure_two_functions_different_args_different_result(f1, f2):
    r1 = f1(1, 2)
    r2 = f2(3, 4)
    assume(r1 != r2)
    # If this is never true, the test will fail with Unsatisfiable


@given(
    f1=functions(like=pure_func, returns=integers(), pure=True),
    f2=functions(like=pure_func, returns=integers(), pure=True),
    arg1=integers(),
    arg2=integers(),
)
def test_functions_pure_two_functions_same_args_different_result(f1, f2, arg1, arg2):
    r1 = f1(arg1, arg2)
    r2 = f2(arg1, arg2)
    assume(r1 != r2)
    # If this is never true, the test will fail with Unsatisfiable


@settings(verbosity=Verbosity.verbose)
@given(functions(returns=booleans(), pure=False))
def test_functions_note_all_calls_to_impure_functions(f):
    ls = []
    with with_reporter(ls.append):
        f()
        f()
    assert len(ls) == 2


@settings(verbosity=Verbosity.verbose)
@given(functions(returns=booleans(), pure=True))
def test_functions_note_only_first_to_pure_functions(f):
    ls = []
    with with_reporter(ls.append):
        f()
        f()
    assert len(ls) == 1


@pytest.mark.parametrize("pure", [False, True])
def test_functions_note_no_calls_to_constant_functions(pure):
    @settings(verbosity=Verbosity.verbose)
    @given(functions(returns=st.just(1), pure=pure))
    def test(f):
        ls = []
        with with_reporter(ls.append):
            f()
            f()
        assert ls == []

    test()


def func_d(x):
    pass


def failing_output(test):
    with capture_out() as out, pytest.raises(AssertionError) as exc_info:
        test()
    return out.getvalue() + "\n".join(getattr(exc_info.value, "__notes__", []))


@pytest.mark.parametrize("pure", [False, True])
@pytest.mark.parametrize(
    "returns,expected",
    [
        (st.just(3), "lambda x: 3"),
        (st.none(), "lambda x: None"),
        (st.sampled_from(["only"]), "lambda x: 'only'"),
    ],
)
def test_constant_functions_are_shown_as_lambdas(returns, expected, pure):
    @given(f=functions(like=func_d, returns=returns, pure=pure))
    def test(f):
        f(1)
        raise AssertionError

    output = failing_output(test)
    assert f"f={expected}," in output
    assert "Called function" not in output


@given(f=functions(like=func_d, returns=st.just(3)))
def test_constant_functions_have_a_constant_lambda_repr(f):
    assert nicerepr(f) == "lambda x: 3"


@pytest.mark.parametrize(
    "returns",
    [st.just(3).map(str), st.just(3).filter(bool), st.sampled_from([1, 2])],
)
def test_non_constant_functions_still_note_their_calls(returns):
    @given(f=functions(like=func_d, returns=returns))
    def test(f):
        f(1)
        raise AssertionError

    output = failing_output(test)
    assert "f=func_d," in output
    assert "Called function: func_d(1) ->" in output


def test_functions_supports_find():
    f = find(
        st.functions(like=pure_func, returns=st.integers(), pure=True), lambda x: True
    )
    with pytest.raises(InvalidState):
        f(1, 2)
    assert f.__name__ == pure_func.__name__
