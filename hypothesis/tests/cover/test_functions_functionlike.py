# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import inspect
import types
from functools import WRAPPER_ASSIGNMENTS, partial, wraps

import pytest

from hypothesis import given, settings, strategies as st

TOKEN = "explicit return"


def prototype(kind, *, same_namespace=False):
    declared = types.ModuleType("functionlike_declared")
    exec(
        "from __future__ import annotations\n"
        "Alias = bytes\n"
        "def declared(prefix: float, item: Alias) -> Alias:\n"
        "    raise AssertionError('declaration called')\n",
        declared.__dict__,
    )
    called = types.ModuleType("functionlike_called")
    called.Alias = bytes if same_namespace else tuple[int, str]
    exec(
        "from __future__ import annotations\n"
        "def called(self, prefix: float, item: Alias) -> Alias:\n"
        "    raise AssertionError('prototype called')\n",
        called.__dict__,
    )

    class Callable:
        __call__ = called.called

    target = Callable()
    # This is meaningful function metadata only for the functionlike shape.
    # The ordinary callable's unrelated globals must not replace __call__'s.
    target.__globals__ = declared.__dict__
    if kind != "instance":
        for name in (
            "__name__",
            "__qualname__",
            "__doc__",
            "__module__",
            "__code__",
            "__defaults__",
            "__kwdefaults__",
            "__annotations__",
        ):
            setattr(target, name, getattr(declared.declared, name))
    if kind == "code-shaped":
        # Original impersonate() accepts this metadata, but inspect does not
        # treat it as a Python code object when choosing the signature source.
        target.__code__ = types.SimpleNamespace(
            co_filename=declared.declared.__code__.co_filename,
            co_firstlineno=declared.declared.__code__.co_firstlineno,
        )
    return target


def check_inferred_value(data, first, use_partial, consumer, expected):
    if consumer == "functions":
        second = data.draw(st.functions(like=first))
        value = second(b"argument") if use_partial else second(7.0, b"argument")
    else:
        seen = []

        @wraps(first, assigned=(*WRAPPER_ASSIGNMENTS, "__annotations__"))
        def capture(**kwargs):
            seen.append(kwargs)
            return first(**kwargs)

        assert data.draw(st.builds(capture)) == TOKEN
        value = seen[0]["item"]
    assert type(value) is expected
    if expected is tuple:
        assert len(value) == 2
        assert type(value[0]) is int
        assert type(value[1]) is str


@pytest.mark.parametrize("use_partial", [False, True])
@pytest.mark.parametrize("same_namespace", [False, True])
@pytest.mark.parametrize("consumer", ["functions", "builds"])
@settings(max_examples=3, derandomize=True, database=None, deadline=None)
@given(data=st.data())
def test_functionlike_metadata_keeps_existing_annotation_policy(
    use_partial, same_namespace, consumer, data
):
    target = prototype("functionlike", same_namespace=same_namespace)
    if use_partial:
        target = partial(target, 7.0)
    first = data.draw(st.functions(like=target, returns=st.just(TOKEN)))
    assert inspect.signature(first, follow_wrapped=False) == inspect.signature(
        target, follow_wrapped=False
    )
    assert (first(b"argument") if use_partial else first(7.0, b"argument")) == TOKEN
    check_inferred_value(data, first, use_partial, consumer, bytes)


@pytest.mark.parametrize("kind", ["instance", "code-shaped"])
@pytest.mark.parametrize("use_partial", [False, True])
@pytest.mark.parametrize("consumer", ["functions", "builds"])
@settings(max_examples=3, derandomize=True, database=None, deadline=None)
@given(data=st.data())
def test_metadata_compatibility_is_distinct_from_signature_selection(
    kind, use_partial, consumer, data
):
    target = prototype(kind)
    if use_partial:
        target = partial(target, 7.0)
    first = data.draw(st.functions(like=target, returns=st.just(TOKEN)))
    assert inspect.signature(first, follow_wrapped=False) == inspect.signature(
        target, follow_wrapped=False
    )
    expected = bytes if kind == "code-shaped" and not use_partial else tuple
    check_inferred_value(data, first, use_partial, consumer, expected)


@pytest.mark.parametrize("boundary", ["custom-signature", "partial-functionlike"])
@pytest.mark.parametrize("consumer", ["functions", "builds"])
@settings(max_examples=3, derandomize=True, database=None, deadline=None)
@given(data=st.data())
def test_ambiguous_annotation_context_keeps_concrete_signature(
    boundary, consumer, data
):
    def called(prefix: float, item: tuple[int, str]) -> tuple[int, str]:
        raise AssertionError("prototype called")

    def overridden(item: bytes) -> bytes:
        raise AssertionError("metadata declaration called")

    target = partial(called, 7.0)
    if boundary == "custom-signature":
        target.__signature__ = inspect.signature(overridden)
    else:
        for name in (
            "__name__",
            "__code__",
            "__defaults__",
            "__kwdefaults__",
            "__annotations__",
        ):
            setattr(target, name, getattr(overridden, name))
        target.__globals__ = overridden.__globals__
        inner = target
        target = partial(inner)
        assert target.func is inner

    signature = inspect.signature(target, follow_wrapped=False)
    annotation = signature.return_annotation
    assert tuple(signature.parameters) == ("item",)
    assert signature.parameters["item"].annotation == annotation
    if boundary == "custom-signature":
        assert annotation is bytes
    else:
        # inspect selects functionlike metadata before partials on Python 3.12,
        # and the underlying callable before that metadata on Python 3.14.
        assert annotation in (bytes, tuple[int, str])
    first = data.draw(st.functions(like=target, returns=st.just(TOKEN)))
    assert inspect.signature(first, follow_wrapped=False) == signature
    assert first(b"argument") == TOKEN
    expected = bytes if annotation is bytes else tuple
    check_inferred_value(
        data, first, use_partial=True, consumer=consumer, expected=expected
    )
    # Concrete annotations do not consult globals, so the public output alone
    # cannot distinguish an absent origin from an invented, unused namespace.
    assert not hasattr(first, "_hypothesis_internal_annotation_origin")
