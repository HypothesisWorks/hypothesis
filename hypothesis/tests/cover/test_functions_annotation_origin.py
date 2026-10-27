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
import sys
import types
import typing
from functools import WRAPPER_ASSIGNMENTS, partial, wraps
from unittest.mock import MagicMock

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.internal.compat import get_type_hints

RUN = settings(max_examples=3, derandomize=True, database=None, deadline=None)
TOKEN = (149, "generated")


def module(name, source, **bindings):
    result = types.ModuleType(name)
    result.__dict__.update(bindings)
    exec("from __future__ import annotations\n" + source, result.__dict__)
    sys.modules[name] = result
    return result


def source(alias="bytes"):
    return module(
        "annotation_origin_source",
        f"""
Result = tuple[int, str]
bytes = Result
str = list[int]
int = Result
calls = []
def named(item: {alias}) -> {alias}:
    raise AssertionError('named body')
def bound(prefix: float, item: {alias}) -> {alias}:
    raise AssertionError('bound body')
class Plain:
    def __call__(self, item: {alias}) -> {alias}:
        raise AssertionError('instance body')
class Bound:
    def __call__(self, prefix: float, item: {alias}) -> {alias}:
        raise AssertionError('bound instance body')
class Init:
    item: complex
    def __init__(self, item: {alias}) -> None:
        raise AssertionError('init body')
class New:
    def __new__(cls, item: {alias}) -> {alias}:
        raise AssertionError('new body')
class Meta(type):
    def __call__(cls, item: {alias}) -> {alias}:
        raise AssertionError('metaclass body')
class WithMeta(metaclass=Meta):
    pass
def tick():
    calls.append('evaluated')
    return Result
class Counted:
    def __call__(self, item: float) -> tick():
        raise AssertionError('counted body')
class Unknown:
    def __call__(self, item: float) -> NeverKnown:
        raise AssertionError('unknown body')
""",
    )


def like(shape, owner):
    if shape == "inherited":
        foreign = module(
            "annotation_origin_child", "class Child(Parent): pass", Parent=owner.Plain
        )
        return foreign.Child()
    return {
        "instance": owner.Plain(),
        "partial-instance": partial(owner.Bound(), 151.0),
        "named-partial": partial(owner.bound, 151.0),
        "init": owner.Init,
        "new": owner.New,
        "meta": owner.WithMeta,
    }[shape]


def check_value(value, alias="bytes"):
    if alias == "bytes":
        assert isinstance(value, tuple), f"declaring alias lost: {value!r}"
        assert len(value) == 2
        assert isinstance(value[0], int)
        assert isinstance(value[1], str)
    else:
        assert isinstance(value, list), f"alternate alias lost: {value!r}"
        assert all(isinstance(item, int) for item in value)


@pytest.mark.parametrize("alias", ["bytes", "str"])
@pytest.mark.parametrize(
    "shape",
    ["instance", "partial-instance", "named-partial", "new", "meta", "inherited"],
)
@RUN
@given(data=st.data())
def test_generated_annotations_retain_declaring_builtin_alias(shape, alias, data):
    owner = source(alias)
    assert typing.get_type_hints(owner.Plain.__call__)["return"] == getattr(
        owner, alias
    )
    first = data.draw(st.functions(like=like(shape, owner), returns=st.just(TOKEN)))
    assert first((157, "argument")) == TOKEN
    second = data.draw(st.functions(like=first))
    check_value(second((157, "argument")), alias)


@pytest.mark.parametrize(
    "shape", ["instance", "partial-instance", "init", "new", "meta", "inherited"]
)
@RUN
@given(data=st.data())
def test_builds_uses_copied_parameter_origin(shape, data):
    owner = source()
    first = data.draw(st.functions(like=like(shape, owner), returns=st.just(TOKEN)))
    seen = []

    @wraps(first, assigned=(*WRAPPER_ASSIGNMENTS, "__annotations__"))
    def capture(**kwargs):
        seen.append(kwargs)
        return first(**kwargs)

    assert data.draw(st.builds(capture)) == TOKEN
    check_value(seen[0]["item"])
    assert "prefix" not in seen[0]


@pytest.mark.parametrize("depth", [1, 3])
@pytest.mark.parametrize("copy_mapping", [False, True])
@RUN
@given(data=st.data())
def test_generated_origin_survives_generation_and_mapping_copy(
    depth, copy_mapping, data
):
    current = data.draw(st.functions(like=source().Plain(), returns=st.just(TOKEN)))
    for _ in range(depth):
        if copy_mapping:
            current.__annotations__ = dict(current.__annotations__)
        current = data.draw(st.functions(like=current))
        check_value(current((163, "argument")))


@pytest.mark.parametrize("depth", [1, 3])
@pytest.mark.parametrize("consumer", ["functions", "builds"])
@RUN
@given(data=st.data())
def test_explicit_annotation_copy_wrappers_retain_origin(depth, consumer, data):
    first = data.draw(st.functions(like=source().Plain(), returns=st.just(TOKEN)))
    current = first
    seen = []

    def wrap(fn):
        @wraps(fn, assigned=(*WRAPPER_ASSIGNMENTS, "__annotations__"))
        def inner(item):
            seen.append({"item": item})
            return fn(item=item)

        return inner

    for _ in range(depth):
        current = wrap(current)
    if consumer == "functions":
        second = data.draw(st.functions(like=current))
        check_value(second((167, "argument")))
    else:
        assert data.draw(st.builds(current)) == TOKEN
        check_value(seen[0]["item"])


@pytest.mark.parametrize("kind", ["raw", "selective-wraps", "replace-mapping"])
@pytest.mark.parametrize("use_partial", [False, True])
@RUN
@given(data=st.data())
def test_separately_authored_wrapper_hints_keep_normal_policy(kind, use_partial, data):
    owner = source()
    own = module(
        "annotation_origin_user_wrapper",
        "def wrapper(item: int) -> int:\n    raise AssertionError('user wrapper body')",
    )
    wrapper = own.wrapper
    own_annotations = wrapper.__annotations__
    if kind == "raw":
        wrapper.__wrapped__ = owner.Plain()
    else:
        first = data.draw(st.functions(like=owner.Plain(), returns=st.just(TOKEN)))
        if kind == "selective-wraps":
            wraps(
                first, assigned=("__name__", "__module__", "__doc__", "__qualname__")
            )(wrapper)
        else:
            wraps(first)(wrapper)
            wrapper.__annotations__ = own_annotations
    assert typing.get_type_hints(wrapper)["return"] is int
    target = partial(wrapper) if use_partial else wrapper
    generated = data.draw(st.functions(like=target))
    assert type(generated(173)) is int
    second = data.draw(st.functions(like=generated))
    assert type(second(173)) is int


@pytest.mark.parametrize("copy_first", [False, True])
@RUN
@given(data=st.data())
def test_generated_concrete_overrides_remain_authoritative(copy_first, data):
    first = data.draw(st.functions(like=source().Plain(), returns=st.just(TOKEN)))
    if copy_first:
        first.__annotations__ = dict(first.__annotations__)
    first.__annotations__["return"] = list[float]
    assert get_type_hints(first)["return"] == list[float]
    second = data.draw(st.functions(like=first))
    result = second((179, "argument"))
    assert isinstance(result, list)
    assert all(isinstance(item, float) for item in result)
    check_value(data.draw(st.builds(first)))


@RUN
@given(data=st.data())
def test_partial_of_generated_function_rebinds_reduced_annotation_origin(data):
    first = data.draw(st.functions(like=source().Bound(), returns=st.just(TOKEN)))
    second = data.draw(st.functions(like=partial(first, 181.0), returns=st.just(TOKEN)))
    third = data.draw(st.functions(like=second))
    check_value(third((191, "argument")))
    assert set(get_type_hints(third)) == {"item", "return"}
    assert list(inspect.signature(third).parameters) == ["item"]
    with pytest.raises(TypeError):
        third(prefix=193.0, item=(197, "argument"))


@RUN
@given(data=st.data())
def test_copied_origin_reads_live_declaring_globals(data):
    owner = source()
    first = data.draw(st.functions(like=owner.Plain(), returns=st.just(TOKEN)))
    owner.bytes = list[str]
    second = data.draw(st.functions(like=first))
    result = second((199, "argument"))
    assert isinstance(result, list)
    assert all(isinstance(item, str) for item in result)
    owner.bytes = dict[int, str]
    third = data.draw(st.functions(like=second))
    result = third((211, "argument"))
    assert isinstance(result, dict)
    assert all(isinstance(k, int) and isinstance(v, str) for k, v in result.items())


@RUN
@given(data=st.data())
def test_recording_annotation_origin_does_not_evaluate_expressions(data):
    owner = source()
    current = owner.Counted()
    for _ in range(3):
        current = data.draw(st.functions(like=current, returns=st.just(TOKEN)))
        assert current(223.0) == TOKEN
    assert owner.calls == []


@RUN
@given(data=st.data())
def test_origin_preserves_genuinely_unresolved_fallback(data):
    first = data.draw(st.functions(like=source().Unknown(), returns=st.just(TOKEN)))
    second = data.draw(st.functions(like=first))
    assert second(227.0) is None


@RUN
@given(data=st.data())
def test_origin_preserves_unrelated_annotation_exception(data):
    first = data.draw(st.functions(like=source().Plain(), returns=st.just(TOKEN)))
    first.__annotations__ = {"item": float, "return": "1 / 0"}
    with pytest.raises(ZeroDivisionError):
        data.draw(st.functions(like=first))


def decorated_prototype(metadata, *, bind_prefix=False):
    owner = source()
    prefix = "prefix: float, " if bind_prefix else ""
    foreign = module(
        "annotation_origin_foreign_function",
        f"def foreign({prefix}item: str) -> str:\n"
        "    raise AssertionError('foreign prototype body')",
    )
    target = owner.Bound() if bind_prefix else owner.Plain()
    assert typing.get_type_hints(type(target).__call__)["return"] == tuple[int, str]
    if metadata != "plain":
        wraps(foreign.foreign)(target)
        if metadata == "without-wrapped":
            del target.__wrapped__
    return partial(target, 229.0) if bind_prefix else target


def inferred_from_generated(data, first, consumer):
    if consumer == "functions":
        second = data.draw(st.functions(like=first))
        return second(TOKEN)
    seen = []

    @wraps(first, assigned=(*WRAPPER_ASSIGNMENTS, "__annotations__"))
    def capture(**kwargs):
        seen.append(kwargs)
        return first(**kwargs)

    assert data.draw(st.builds(capture)) == TOKEN
    assert set(seen[0]) == {"item"}
    return seen[0]["item"]


@pytest.mark.parametrize("metadata", ["plain", "decorated", "without-wrapped"])
@pytest.mark.parametrize("consumer", ["functions", "builds"])
@RUN
@given(data=st.data())
def test_copied_callable_annotations_ignore_wrapper_metadata(metadata, consumer, data):
    target = decorated_prototype(metadata)
    expected = inspect.signature(target, follow_wrapped=False)
    first = data.draw(st.functions(like=target, returns=st.just(TOKEN)))
    assert inspect.signature(first, follow_wrapped=False) == expected
    assert first(TOKEN) == TOKEN
    check_value(inferred_from_generated(data, first, consumer))


@pytest.mark.parametrize("metadata", ["plain", "decorated"])
@pytest.mark.parametrize("consumer", ["functions", "builds"])
@RUN
@given(data=st.data())
def test_copied_partial_callable_keeps_own_annotation_context(metadata, consumer, data):
    target = decorated_prototype(metadata, bind_prefix=True)
    expected = inspect.signature(target, follow_wrapped=False)
    assert list(expected.parameters) == ["item"]
    first = data.draw(st.functions(like=target, returns=st.just(TOKEN)))
    assert inspect.signature(first, follow_wrapped=False) == expected
    assert first(TOKEN) == TOKEN
    with pytest.raises(TypeError):
        first(prefix=233.0, item=TOKEN)
    check_value(inferred_from_generated(data, first, consumer))


@pytest.mark.parametrize("consumer", ["functions", "builds"])
@RUN
@given(data=st.data())
def test_copied_partial_authored_wrapper_keeps_typing_namespace(consumer, data):
    underlying = module(
        "annotation_origin_wrapped_function",
        "def wrapped(prefix: float, item: int) -> int:\n"
        "    raise AssertionError('underlying function body')",
    )
    own = module(
        "annotation_origin_authored_function",
        "int = list[str]\n"
        "def wrapper(prefix: float, item: int) -> int:\n"
        "    raise AssertionError('authored wrapper body')",
    )
    annotations = own.wrapper.__annotations__
    wrapper = wraps(
        underlying.wrapped,
        assigned=("__name__", "__module__", "__doc__", "__qualname__"),
    )(own.wrapper)
    assert wrapper.__annotations__ is annotations
    assert typing.get_type_hints(wrapper)["item"] is int
    assert typing.get_type_hints(wrapper)["return"] is int
    target = partial(wrapper, 239.0)
    first = data.draw(st.functions(like=target, returns=st.just(TOKEN)))
    assert inspect.signature(first, follow_wrapped=False) == inspect.signature(
        target, follow_wrapped=False
    )
    assert first(TOKEN) == TOKEN
    assert type(inferred_from_generated(data, first, consumer)) is int


@RUN
@given(data=st.data())
def test_builds_ignores_synthesized_annotation_origin(data):
    def interface(item: int):
        pass

    target = MagicMock(return_value=17)
    target.__signature__ = inspect.signature(interface)
    assert data.draw(st.builds(target)) == 17
    assert type(target.call_args.kwargs["item"]) is int


@pytest.mark.parametrize("marker", [None, (), [], "tuple-shaped"])
@RUN
@given(data=st.data())
def test_builds_ignores_unrelated_annotation_origin(marker, data):
    def target(item: "int"):
        return item

    if marker == "tuple-shaped":
        marker = (target, target.__annotations__, {"int": str})
    target._hypothesis_internal_annotation_origin = marker
    assert type(data.draw(st.builds(target))) is int


@RUN
@given(data=st.data())
def test_builds_does_not_evaluate_foreign_origin_descriptor(data):
    def interface(item: int):
        pass

    class Target:
        __signature__ = inspect.signature(interface)

        @property
        def _hypothesis_internal_annotation_origin(self):
            raise AssertionError("unrelated descriptor evaluated")

        def __call__(self, item):
            return item

    assert type(data.draw(st.builds(Target()))) is int


@RUN
@given(data=st.data())
def test_bound_generated_method_retains_annotation_origin(data):
    owner = module(
        "annotation_origin_bound_method",
        "bytes = tuple[int, str]\n"
        "class Callable:\n"
        "    def __call__(self, receiver: object, item: bytes) -> bytes:\n"
        "        raise AssertionError('prototype body ran')\n",
    )
    first = data.draw(st.functions(like=owner.Callable(), returns=st.just(TOKEN)))
    bound = types.MethodType(first, object())
    second = data.draw(st.functions(like=bound))
    check_value(second(TOKEN))


@pytest.mark.parametrize("shape", ["direct", "instance", "metaclass"])
@pytest.mark.parametrize("consumer", ["functions", "builds"])
@RUN
@given(data=st.data())
def test_selected_special_method_partial_keeps_its_namespace(shape, consumer, data):
    owner = module(
        "annotation_origin_partial_call",
        "bytes = tuple[int, str]\n"
        "def callback(prefix: float, item: bytes) -> bytes:\n"
        "    raise AssertionError('selected prototype body ran')\n",
    )
    foreign = module(
        "annotation_origin_unselected_init",
        "bytes = list[int]\n"
        "def initializer(self, item: bytes) -> None:\n"
        "    raise AssertionError('unselected initializer ran')\n",
    )
    callback = partial(owner.callback, 0.0)

    class Meta(type):
        __call__ = staticmethod(callback)

    class Prototype(metaclass=Meta):
        __init__ = foreign.initializer

    class Instance:
        __call__ = staticmethod(callback)

    target = {"direct": callback, "instance": Instance(), "metaclass": Prototype}[shape]
    assert inspect.signature(target, follow_wrapped=False) == inspect.signature(
        callback
    )
    assert typing.get_type_hints(owner.callback)["return"] == tuple[int, str]
    assert typing.get_type_hints(foreign.initializer)["item"] == list[int]
    first = data.draw(st.functions(like=target, returns=st.just(TOKEN)))
    check_value(inferred_from_generated(data, first, consumer))


@pytest.mark.parametrize("wrap_new", [False, True])
@RUN
@given(data=st.data())
def test_builtin_override_does_not_revive_shadowed_constructor(wrap_new, data):
    allocator = module(
        "annotation_origin_shadowed_allocator",
        "bytes = tuple[int, str]\n"
        "def allocate(cls, item: bytes):\n"
        "    raise AssertionError('shadowed allocator ran')\n",
    )
    initializer = module(
        "annotation_origin_selected_init",
        "bytes = list[int]\n"
        "def initialize(self, item: bytes) -> None:\n"
        "    raise AssertionError('prototype initializer ran')\n",
    )

    class Parent:
        __new__ = staticmethod(allocator.allocate)
        __init__ = initializer.initialize

    class Child(Parent):
        __new__ = staticmethod(object.__new__) if wrap_new else object.__new__

    expected = inspect.signature(initializer.initialize)
    expected = expected.replace(parameters=list(expected.parameters.values())[1:])
    assert inspect.signature(Child, follow_wrapped=False) == expected
    assert typing.get_type_hints(initializer.initialize)["item"] == list[int]
    first = data.draw(st.functions(like=Child, returns=st.just(TOKEN)))
    value = inferred_from_generated(data, first, "builds")
    assert isinstance(value, list)
    assert all(type(item) is int for item in value)


@RUN
@given(data=st.data())
def test_selected_builtin_staticmethod_does_not_borrow_initializer_namespace(data):
    class Meta(type):
        __call__ = staticmethod(list)

    class Prototype(metaclass=Meta):
        def __init__(self, item: int):
            raise AssertionError("unselected initializer ran")

    first = data.draw(st.functions(like=Prototype, returns=st.just(TOKEN)))
    assert inspect.signature(first, follow_wrapped=False) == inspect.signature(list)
    assert first() == TOKEN
    # Concrete/no annotations cannot expose a guessed but unused namespace in
    # the value; this separately guards the conservative provenance policy.
    assert not hasattr(first, "_hypothesis_internal_annotation_origin")


@RUN
@given(data=st.data())
def test_callable_without_annotations_needs_no_interpretation_context(data):
    class Prototype:
        pass

    first = data.draw(st.functions(like=Prototype, returns=st.just(TOKEN)))
    assert first() == TOKEN
    second = data.draw(st.functions(like=first))
    assert second() is None


@pytest.mark.parametrize("shape", ["direct", "static-new", "class-new"])
@pytest.mark.parametrize("consumer", ["functions", "builds"])
@RUN
@given(data=st.data())
def test_bound_partial_constructor_keeps_annotation_namespace(shape, consumer, data):
    owner = module(
        "annotation_origin_bound_partial_constructor",
        "bytes = tuple[int, str]\n"
        "calls = []\n"
        "def allocate(prefix, receiver, cls, item: bytes) -> bytes:\n"
        "    calls.append(item)\n"
        "    return item\n",
    )
    direct = partial(owner.allocate, 0, None, None)

    class StaticNew:
        __new__ = staticmethod(partial(owner.allocate, 0, None))

    class ClassNew:
        __new__ = classmethod(partial(owner.allocate, 0))

    target = {"direct": direct, "static-new": StaticNew, "class-new": ClassNew}[shape]
    assert inspect.signature(target, follow_wrapped=False) == inspect.signature(direct)
    evaluated = inspect.signature(target, follow_wrapped=False, eval_str=True)
    assert evaluated.parameters["item"].annotation == tuple[int, str]
    assert evaluated.return_annotation == tuple[int, str]
    assert target(TOKEN) == TOKEN
    owner.calls.clear()

    first = data.draw(st.functions(like=target, returns=st.just(TOKEN)))
    assert first(TOKEN) == TOKEN
    check_value(inferred_from_generated(data, first, consumer))
    assert owner.calls == []
