# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from collections.abc import AsyncIterator, Iterator
from functools import partial
from inspect import (
    isasyncgenfunction,
    iscoroutinefunction,
    isgeneratorfunction,
    signature,
)

import pytest

from hypothesis import given, strategies as st


def source(a: int, b: str, *, flag: bool = False) -> bytes:
    return b"original"


class CallableLike:
    def __call__(self, b: str, *, flag: bool = False) -> bytes:
        return b"original"


class ClassLike:
    def __init__(self, b: str, *, flag: bool = False):
        self.b = b


class MethodLike:
    def method(self, b: str, *, flag: bool = False) -> bytes:
        return b"original"


LIKES = [
    pytest.param(source, (7, "sample"), {}, id="named_function"),
    pytest.param(lambda b, *, flag=False: b, ("sample",), {}, id="lambda"),
    pytest.param(MethodLike().method, ("sample",), {}, id="bound_method"),
    pytest.param(partial(source, 7), ("sample",), {}, id="positional_partial"),
    pytest.param(partial(source, a=7), (), {"b": "sample"}, id="keyword_partial"),
    pytest.param(
        partial(partial(source, 7), flag=True), ("sample",), {}, id="nested_partial"
    ),
    pytest.param(CallableLike(), ("sample",), {}, id="callable_instance"),
    pytest.param(ClassLike, ("sample",), {}, id="class"),
    pytest.param(len, ([],), {}, id="builtin"),
]


@pytest.mark.parametrize("like,args,kwargs", LIKES)
@pytest.mark.parametrize("sentinel", [17, 29])
@given(data=st.data())
def test_generated_functions_support_inspectable_callables(
    like, args, kwargs, sentinel, data
):
    generated = data.draw(st.functions(like=like, returns=st.just(sentinel)))
    assert signature(generated, follow_wrapped=False) == signature(
        like, follow_wrapped=False
    )
    assert generated(*args, **kwargs) == sentinel
    if hasattr(like, "__name__"):
        assert generated.__name__ == like.__name__
    with pytest.raises(TypeError):
        generated(unexpected_argument=True)


@pytest.mark.parametrize("like,args,kwargs", [LIKES[3], LIKES[4]])
@given(data=st.data())
def test_generated_partial_functions_infer_return_type(like, args, kwargs, data):
    generated = data.draw(st.functions(like=like))
    assert isinstance(generated(*args, **kwargs), bytes)


def run_coroutine(coro):
    while True:
        try:
            coro.send(None)
        except StopIteration as stop:
            return stop.value


async def async_source(a: int, b: str) -> int:
    return 3


def generator_source(a: int, b: str) -> Iterator[int]:
    yield 3


async def async_generator_source(a: int, b: str) -> AsyncIterator[int]:
    yield 3


@given(data=st.data())
def test_generated_coroutine_partial_preserves_kind(data):
    generated = data.draw(
        st.functions(like=partial(async_source, 7), returns=st.just(29))
    )
    assert iscoroutinefunction(generated)
    assert run_coroutine(generated("sample")) == 29


@given(data=st.data())
def test_generated_generator_partial_preserves_kind(data):
    generated = data.draw(
        st.functions(like=partial(generator_source, 7), returns=st.just(29))
    )
    assert isgeneratorfunction(generated)
    values = list(generated("sample"))
    assert all(value == 29 for value in values)


@given(data=st.data())
def test_generated_async_generator_partial_preserves_kind(data):
    generated = data.draw(
        st.functions(like=partial(async_generator_source, 7), returns=st.just(29))
    )
    assert isasyncgenfunction(generated)
    generator = generated("sample")
    while True:
        try:
            assert run_coroutine(generator.__anext__()) == 29
        except StopAsyncIteration:
            break
