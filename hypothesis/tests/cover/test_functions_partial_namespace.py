# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import inspect
import typing
from collections.abc import Iterator
from functools import WRAPPER_ASSIGNMENTS, partial, wraps

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.internal.compat import get_type_hints
from hypothesis.internal.reflection import proxies
from hypothesis.stateful import rule

CallbackResult = tuple[int, str]
OtherResult = bytes
RemainingArgument = str
OverrideResult = list[float]
SOURCE_CALLS = []
RUN = settings(max_examples=3, derandomize=True, database=None, deadline=None)


def callback(
    prefix: int, value: RemainingArgument, *, flag: bool = False
) -> CallbackResult:
    SOURCE_CALLS.append((prefix, value, flag))
    raise AssertionError("the prototype must not be called")


def other_callback(prefix: int, value: RemainingArgument) -> OtherResult:
    raise AssertionError("the prototype must not be called")


def concrete_callback(prefix: int, value: str) -> str:
    raise AssertionError("the prototype must not be called")


def unresolved_callback(
    prefix: int, value: str
) -> DeliberatelyUnknownResult:  # noqa: F821
    raise AssertionError("the prototype must not be called")


@pytest.mark.parametrize(
    "source,expected",
    [(callback, tuple), (other_callback, bytes), (concrete_callback, str)],
)
@pytest.mark.parametrize("use_partial", [False, True])
@RUN
@given(data=st.data())
def test_reconsumption_keeps_resolvable_return_meaning(
    source, expected, use_partial, data
):
    like = partial(source, 11) if use_partial else source
    args = ("remaining",) if use_partial else (11, "remaining")
    first = data.draw(st.functions(like=like, returns=st.just("first-draw")))
    assert first(*args) == "first-draw"
    second = data.draw(st.functions(like=first))
    result = second(*args)
    assert isinstance(result, expected), f"return annotation meaning lost: {result!r}"
    if expected is tuple:
        assert len(result) == 2
        assert isinstance(result[0], int)
        assert isinstance(result[1], str)
    assert SOURCE_CALLS == []


@pytest.mark.parametrize("use_partial", [False, True])
@RUN
@given(data=st.data())
def test_genuinely_unresolved_reconsumption_falls_back(use_partial, data):
    like = partial(unresolved_callback, 13) if use_partial else unresolved_callback
    args = ("remaining",) if use_partial else (13, "remaining")
    first = data.draw(st.functions(like=like, returns=st.just("first-draw")))
    second = data.draw(st.functions(like=first))
    assert second(*args) is None


@RUN
@given(data=st.data())
def test_reconsumption_uses_wrapper_owned_annotations(data):
    first = data.draw(
        st.functions(like=partial(callback, 17), returns=st.just("first-draw"))
    )
    # Intentional wrapper annotations must not be replaced by the prototype's.
    first.__annotations__ = {"value": "OtherResult", "return": "OverrideResult"}
    assert get_type_hints(first) == {"value": bytes, "return": list[float]}
    assert "prefix" not in inspect.signature(first, follow_wrapped=False).parameters
    second = data.draw(st.functions(like=first))
    result = second(b"remaining")
    assert isinstance(result, list)
    assert all(isinstance(value, float) for value in result)


@RUN
@given(data=st.data())
def test_composed_partial_keeps_remaining_arguments(data):
    first = data.draw(
        st.functions(like=partial(callback, 19), returns=st.just("first-draw"))
    )
    second = data.draw(st.functions(like=first))
    assert list(inspect.signature(second, follow_wrapped=False).parameters) == [
        "value",
        "flag",
    ]
    assert isinstance(second("remaining", flag=True), tuple)
    assert isinstance(second(value="remaining"), tuple)
    with pytest.raises(TypeError):
        second()
    with pytest.raises(TypeError):
        second("remaining", True)
    with pytest.raises(TypeError):
        second(prefix=19, value="remaining")


class MethodSource:
    def method(self, prefix: int, value: RemainingArgument) -> CallbackResult:
        raise AssertionError("the prototype must not be called")


@pytest.mark.parametrize(
    "like", [partial(callback, 23), partial(MethodSource().method, 23)]
)
@RUN
@given(data=st.data())
def test_partial_direct_and_composed_return_inference(like, data):
    assert get_type_hints(like)["return"] == tuple[int, str]
    assert "prefix" not in get_type_hints(like)
    first = data.draw(st.functions(like=like))
    assert isinstance(first("remaining"), tuple)
    second = data.draw(st.functions(like=first))
    assert isinstance(second("remaining"), tuple)


@RUN
@given(data=st.data())
def test_mixed_partial_wrapper_chain_uses_owner_namespace(data):
    first = data.draw(
        st.functions(like=partial(callback, 29), returns=st.just("first-draw"))
    )
    second = data.draw(
        st.functions(like=partial(first, "remaining"), returns=st.just("second-draw"))
    )
    third = data.draw(st.functions(like=second))
    assert isinstance(third(flag=True), tuple)
    assert set(get_type_hints(third)) == {"flag", "return"}


@RUN
@given(data=st.data())
def test_builds_can_consume_generated_partial_parameter_hints(data):
    first = data.draw(
        st.functions(like=partial(callback, 31), returns=st.just("first-draw"))
    )
    calls = []

    @wraps(first, assigned=(*WRAPPER_ASSIGNMENTS, "__annotations__"))
    def capture(*args, **kwargs):
        calls.append((args, kwargs))
        return first(*args, **kwargs)

    assert data.draw(st.builds(capture)) == "first-draw"
    assert len(calls) == 1
    assert isinstance(calls[0][1]["value"], str)
    assert "prefix" not in calls[0][1]


def raising_annotation():
    raise AssertionError("explicit returns should not evaluate annotations")


def unevaluated_callback(prefix: int, value: str) -> raising_annotation():
    raise AssertionError("the prototype must not be called")


@RUN
@given(data=st.data())
def test_explicit_returns_do_not_evaluate_partial_annotations(data):
    first = data.draw(
        st.functions(
            like=partial(unevaluated_callback, 37),
            returns=st.just("first-draw"),
        )
    )
    second = data.draw(st.functions(like=first, returns=st.just("second-draw")))
    assert second("remaining") == "second-draw"


def test_successful_normal_hint_lookup_is_not_retried(monkeypatch):
    calls = []
    original = typing.get_type_hints

    def counted(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(typing, "get_type_hints", counted)
    assert get_type_hints(callback)["return"] == tuple[int, str]
    assert len(calls) == 1
    assert "globalns" not in calls[0][1]


def test_unrelated_annotation_exceptions_keep_existing_policy():
    def broken(value):
        return value

    broken.__annotations__ = {"return": "int('deliberately invalid')"}
    with pytest.raises(ValueError):
        get_type_hints(broken)


def test_normal_function_metadata_and_rule_metadata_are_preserved():
    def source(self, value: int) -> str:
        """Source documentation."""
        return str(value)

    source.marker = object()
    source.__annotations__["nonparameter_metadata"] = bytes
    # Match the runtime's default wrapping policy, including lazy annotations.
    reference = wraps(source)(lambda *args, **kwargs: None)
    wrapped = rule(value=st.integers())(source)
    assert wrapped.__annotations__ == reference.__annotations__
    assert wrapped.marker is source.marker
    assert wrapped.__name__ == source.__name__
    assert wrapped.__qualname__ == source.__qualname__
    assert wrapped.__module__ == source.__module__
    assert wrapped.__doc__ == source.__doc__
    assert wrapped.__code__.co_filename == source.__code__.co_filename
    assert wrapped.__code__.co_firstlineno == source.__code__.co_firstlineno
    assert inspect.signature(wrapped) == inspect.signature(source)


def test_normal_bound_method_metadata_is_preserved():
    method = MethodSource().method

    @proxies(method)
    def wrapped(*args, **kwargs):
        return args, kwargs

    assert wrapped.__annotations__ == method.__annotations__
    assert wrapped.__name__ == method.__name__
    assert list(inspect.signature(wrapped, follow_wrapped=False).parameters) == [
        "prefix",
        "value",
    ]
    assert wrapped(41, "remaining") == ((41, "remaining"), {})


async def async_callback(prefix: int, value: RemainingArgument) -> CallbackResult:
    raise AssertionError("the prototype must not be called")


def generator_callback(prefix: int, value: RemainingArgument) -> Iterator[OtherResult]:
    raise AssertionError("the prototype must not be called")
    yield b"never"


def finish(coro):
    while True:
        try:
            coro.send(None)
        except StopIteration as result:
            return result.value


@RUN
@given(data=st.data())
def test_async_partial_reconsumption(data):
    first = data.draw(
        st.functions(like=partial(async_callback, 43), returns=st.just("first-draw"))
    )
    second = data.draw(st.functions(like=first))
    assert inspect.iscoroutinefunction(second)
    assert isinstance(finish(second("remaining")), tuple)


@RUN
@given(data=st.data())
def test_generator_partial_reconsumption(data):
    first = data.draw(
        st.functions(
            like=partial(generator_callback, 47),
            returns=st.just(b"first-draw"),
        )
    )
    second = data.draw(st.functions(like=first))
    assert inspect.isgeneratorfunction(second)
    values = list(second("remaining"))
    assert all(isinstance(value, bytes) for value in values)
    assert get_type_hints(second)["return"] == Iterator[bytes]
