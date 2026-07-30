# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from collections.abc import (
    AsyncIterator,
    Generator,
    Iterator,
)
from inspect import (
    isasyncgenfunction,
    iscoroutinefunction,
    isgeneratorfunction,
    signature,
)

import pytest

from hypothesis import Verbosity, assume, find, given, settings, strategies as st
from hypothesis.errors import InvalidArgument, InvalidState
from hypothesis.internal.reflection import nicerepr
from hypothesis.reporting import with_reporter
from hypothesis.strategies import booleans, functions, integers

from tests.common.debug import assert_all_examples, check_can_generate_examples
from tests.common.utils import capture_out


def run_coroutine(coro):
    # Generated async functions only await checkpoints, which never block, so
    # we can pump the coroutine to completion without an event loop.
    while True:
        try:
            coro.send(None)
        except StopIteration as e:
            return e.value


def collect_async_gen(agen):
    values = []
    while True:
        try:
            values.append(run_coroutine(agen.__anext__()))
        except StopAsyncIteration:
            return values


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


def test_constant_async_functions_note_their_calls_instead():
    # A lambda would be a poor description of an async function, so we note
    # calls as usual even when we know what awaiting them will return.
    @given(f=functions(like=async_func, returns=st.just(3)))
    def test(f):
        run_coroutine(f(1))
        raise AssertionError

    output = failing_output(test)
    assert "lambda" not in output
    assert "Called function" in output


raw_object = object()


@given(f=functions(like=lambda x=raw_object: None, returns=st.just(3)))
def test_constant_functions_show_default_values_by_repr(f):
    # This is strictly speaking not valid syntax (contains memory marker like <...>),
    # but we show it anyway.
    assert nicerepr(f) == f"lambda x={raw_object!r}: 3"


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


async def async_func(a: int) -> str:
    raise NotImplementedError


@given(functions(like=async_func))
def test_async_functions_infer_return_type(f):
    assert iscoroutinefunction(f)
    assert f.__name__ == "async_func"
    with pytest.raises(TypeError):
        f()
    assert isinstance(run_coroutine(f(1)), str)


@given(functions(like=async_func, returns=integers()))
def test_async_functions_explicit_returns(f):
    assert isinstance(run_coroutine(f(1)), int)


def test_async_functions_invalid_outside_given():
    cached = None

    @given(functions(like=async_func))
    def t(f):
        nonlocal cached
        cached = f
        run_coroutine(f(1))

    t()
    with pytest.raises(InvalidState):
        run_coroutine(cached(1))


def gen_func(a: int) -> Iterator[bool]:
    yield True


@given(functions(like=gen_func))
def test_generator_functions_infer_yield_type(f):
    assert isgeneratorfunction(f)
    assert f.__name__ == "gen_func"
    with pytest.raises(TypeError):
        f()
    for value in f(1):
        assert isinstance(value, bool)


@given(functions(like=gen_func, returns=integers()))
def test_generator_functions_explicit_returns(f):
    for value in f(1):
        assert isinstance(value, int)


def gen_func_with_return(a) -> Generator[bool, None, int]:
    yield True
    return 0


@given(functions(like=gen_func_with_return))
def test_generator_functions_infer_yield_type_ignoring_send_and_return(f):
    for value in f(1):
        assert isinstance(value, bool)


def gen_func_no_annotation():
    yield


@given(functions(like=gen_func_no_annotation))
def test_unannotated_generator_functions_yield_none(f):
    # With no annotation to infer a yield type from, we fall back to none()
    # just as we do for the return value of plain functions.
    assert all(value is None for value in f())


def test_generator_functions_invalid_outside_given():
    cached = None

    @given(functions(like=gen_func))
    def t(f):
        nonlocal cached
        cached = f
        list(f(1))

    t()
    with pytest.raises(InvalidState):
        list(cached(1))


def test_can_close_generated_generators_early():
    @given(functions(like=gen_func, returns=booleans()))
    def t(f):
        gen = f(1)
        next(gen, None)
        gen.close()

    t()


async def async_gen_func(a: int) -> AsyncIterator[bool]:
    yield True


@given(functions(like=async_gen_func))
def test_async_generator_functions_infer_yield_type(f):
    assert isasyncgenfunction(f)
    assert f.__name__ == "async_gen_func"
    with pytest.raises(TypeError):
        f()
    for value in collect_async_gen(f(1)):
        assert isinstance(value, bool)


@given(functions(like=async_gen_func, returns=integers()))
def test_async_generator_functions_explicit_returns(f):
    for value in collect_async_gen(f(1)):
        assert isinstance(value, int)


async def async_gen_func_no_annotation():
    yield


@given(functions(like=async_gen_func_no_annotation))
def test_unannotated_async_generator_functions_yield_none(f):
    assert all(value is None for value in collect_async_gen(f()))


def test_can_close_generated_async_generators_early():
    @given(functions(like=async_gen_func, returns=booleans()))
    def t(f):
        agen = f(1)
        try:
            run_coroutine(agen.__anext__())
        except StopAsyncIteration:
            pass
        run_coroutine(agen.aclose())

    t()


@pytest.mark.parametrize("like", [async_func, gen_func, async_gen_func])
def test_pure_is_invalid_except_for_plain_functions(like):
    with pytest.raises(InvalidArgument, match="pure=True is invalid"):
        check_can_generate_examples(functions(like=like, pure=True))


def make_gen_like(annotation, *, is_async=False):
    prefix = "async " if is_async else ""
    # pass our globals so we can reference things like the module-level IteratorSubclass
    # in test strings
    namespace = dict(globals())
    exec(
        f"from collections.abc import *\n{prefix}def like(a) -> {annotation}:\n    yield",
        namespace,
    )
    return namespace["like"]


class IteratorSubclass(Iterator[bool]):
    def __next__(self):
        raise StopIteration


@pytest.mark.parametrize(
    "annotation",
    ["Iterator[bool]", "Iterable[bool]", "Generator[bool, None, None]"],
)
def test_generator_functions_accept_any_iterator_like_annotation(annotation):
    assert_all_examples(
        functions(like=make_gen_like(annotation)),
        lambda f: all(isinstance(value, bool) for value in f(1)),
    )


@pytest.mark.parametrize(
    "annotation",
    ["AsyncIterator[bool]", "AsyncIterable[bool]", "AsyncGenerator[bool, None]"],
)
def test_async_generator_functions_accept_any_async_iterator_like_annotation(
    annotation,
):
    assert_all_examples(
        functions(like=make_gen_like(annotation, is_async=True)),
        lambda f: all(isinstance(value, bool) for value in collect_async_gen(f(1))),
    )


@pytest.mark.parametrize(
    "annotation",
    [
        "bool",
        "tuple[bool, str]",
        "list[bool]",
        "IteratorSubclass",
        "AsyncIterator[bool]",
    ],
)
def test_generator_functions_reject_other_annotations(annotation):
    with pytest.raises(InvalidArgument, match="Cannot infer the yield type"):
        check_can_generate_examples(functions(like=make_gen_like(annotation)))


@pytest.mark.parametrize(
    "annotation",
    ["bool", "tuple[bool, str]", "list[bool]", "Iterator[bool]"],
)
def test_async_generator_functions_reject_other_annotations(annotation):
    with pytest.raises(InvalidArgument, match="Cannot infer the yield type"):
        check_can_generate_examples(
            functions(like=make_gen_like(annotation, is_async=True))
        )
