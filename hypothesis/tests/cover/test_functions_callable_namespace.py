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
from functools import WRAPPER_ASSIGNMENTS, partial, wraps

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.internal.compat import get_type_hints

RUN = settings(max_examples=3, derandomize=True, database=None, deadline=None)
TOKEN = (103, "generated")


def owners():
    owner = types.ModuleType("callable_annotation_owner")
    exec(
        """from __future__ import annotations
Result = tuple[int, str]
Alternate = bytes
calls = []
def named(item: Result) -> Result:
    raise AssertionError('named prototype called')
class Plain:
    def __call__(self, item: Result) -> Result:
        raise AssertionError('instance prototype called')
class Bound:
    def __call__(self, prefix: int, item: Result) -> Result:
        raise AssertionError('bound prototype called')
class Constructor:
    item: complex
    def __init__(self, item: Result, *, flag: bool = False) -> None:
        raise AssertionError('constructor called')
class NewConstructor:
    def __new__(cls, item: Result) -> Result:
        raise AssertionError('new constructor called')
    def __init__(self, item: Alternate) -> None:
        raise AssertionError('init constructor called')
class Meta(type):
    def __call__(cls, item: Result) -> Result:
        raise AssertionError('metaclass called')
class MetaConstructor(metaclass=Meta):
    def __init__(self, item: Alternate) -> None:
        raise AssertionError('metaclass constructor called')
class StaticCallable:
    @staticmethod
    def __call__(item: Result) -> Result:
        raise AssertionError('static callable called')
class ClassCallable:
    @classmethod
    def __call__(cls, item: Result) -> Result:
        raise AssertionError('class callable called')
def tick():
    calls.append('evaluated')
    return Result
class Counted:
    def __call__(self, item: Result) -> tick():
        raise AssertionError('counted prototype called')
class Unknown:
    def __call__(self, item: int) -> DeliberatelyUnknown:
        raise AssertionError('unknown prototype called')
""",
        owner.__dict__,
    )
    foreign = types.ModuleType("callable_foreign_owner")
    foreign.Parent = owner.Plain
    foreign.BaseConstructor = owner.Constructor
    foreign.BaseNew = owner.NewConstructor
    exec(
        """from __future__ import annotations
Result = bytes
Alternate = str
class Child(Parent):
    pass
class ChildConstructor(BaseConstructor):
    item: Result
class ChildInit(BaseNew):
    def __init__(self, item: Result) -> None:
        raise AssertionError('child constructor called')
def foreign_init(self, item: Result) -> None:
    raise AssertionError('foreign initializer called')
def decoy(item: Result) -> Result:
    raise AssertionError('instance attribute called')
""",
        foreign.__dict__,
    )
    # Give the unselected initializers a different annotation namespace.
    owner.NewConstructor.__init__ = foreign.foreign_init
    owner.MetaConstructor.__init__ = foreign.foreign_init
    sys.modules[owner.__name__] = owner
    sys.modules[foreign.__name__] = foreign
    return owner, foreign


def pair(value):
    assert isinstance(value, tuple), f"annotation meaning lost: {value!r}"
    assert len(value) == 2
    assert isinstance(value[0], int)
    assert isinstance(value[1], str)


def select(shape, owner, foreign):
    if shape == "instance":
        return owner.Plain()
    if shape == "partial-instance":
        return partial(owner.Bound(), 107)
    if shape == "inherited-instance":
        return foreign.Child()
    if shape == "shadow-instance-call":
        instance = owner.Plain()
        instance.__call__ = foreign.decoy
        return instance
    return {
        "named": owner.named,
        "constructor": owner.Constructor,
        "inherited-constructor": foreign.ChildConstructor,
        "new-constructor": owner.NewConstructor,
        "child-init": foreign.ChildInit,
        "metaclass": owner.MetaConstructor,
        "static-call": owner.StaticCallable(),
        "class-call": owner.ClassCallable(),
    }[shape]


@pytest.mark.parametrize(
    "shape",
    [
        "named",
        "instance",
        "partial-instance",
        "inherited-instance",
        "shadow-instance-call",
        "static-call",
        "class-call",
        "new-constructor",
        "metaclass",
    ],
)
@RUN
@given(data=st.data())
def test_generated_callable_reconsumption_uses_invocation_namespace(shape, data):
    owner, foreign = owners()
    like = select(shape, owner, foreign)
    first = data.draw(st.functions(like=like, returns=st.just(TOKEN)))
    assert first((109, "argument")) == TOKEN
    second = data.draw(st.functions(like=first))
    pair(second((109, "argument")))
    assert owner.calls == []


@pytest.mark.parametrize(
    "shape,argument_type",
    [
        ("instance", tuple),
        ("partial-instance", tuple),
        ("inherited-instance", tuple),
        ("shadow-instance-call", tuple),
        ("constructor", tuple),
        ("inherited-constructor", tuple),
        ("new-constructor", tuple),
        ("child-init", bytes),
        ("metaclass", tuple),
    ],
)
@RUN
@given(data=st.data())
def test_builds_uses_callable_interface_annotation_owner(shape, argument_type, data):
    owner, foreign = owners()
    first = data.draw(
        st.functions(like=select(shape, owner, foreign), returns=st.just(TOKEN))
    )
    calls = []

    @wraps(first, assigned=(*WRAPPER_ASSIGNMENTS, "__annotations__"))
    def capture(**kwargs):
        calls.append(kwargs)
        return first(**kwargs)

    assert data.draw(st.builds(capture)) == TOKEN
    assert len(calls) == 1
    assert isinstance(calls[0]["item"], argument_type)
    assert "prefix" not in calls[0]
    assert "self" not in calls[0]
    assert "cls" not in calls[0]


@pytest.mark.parametrize("shape", ["instance", "partial-instance", "constructor"])
@RUN
@given(data=st.data())
def test_callable_wrapper_owned_annotations_override_source(shape, data):
    owner, foreign = owners()
    first = data.draw(
        st.functions(like=select(shape, owner, foreign), returns=st.just(TOKEN))
    )
    first.__annotations__ = {"item": "Alternate", "return": "Alternate"}
    assert get_type_hints(first) == {"item": bytes, "return": bytes}
    second = data.draw(st.functions(like=first))
    assert isinstance(second(b"argument"), bytes)


@RUN
@given(data=st.data())
def test_partial_instance_wrapper_chain_keeps_remaining_interface(data):
    owner, _ = owners()
    first = data.draw(
        st.functions(like=partial(owner.Bound(), 113), returns=st.just(TOKEN))
    )
    second = data.draw(
        st.functions(like=partial(first, (127, "bound")), returns=st.just(TOKEN))
    )
    third = data.draw(st.functions(like=second))
    pair(third())
    assert set(get_type_hints(third)) == {"return"}
    assert len(inspect.signature(third).parameters) == 0
    with pytest.raises(TypeError):
        third("unexpected")


@pytest.mark.parametrize("use_partial", [False, True])
@RUN
@given(data=st.data())
def test_callable_explicit_returns_do_not_evaluate_annotations(use_partial, data):
    owner, _ = owners()
    like = partial(owner.Counted()) if use_partial else owner.Counted()
    first = data.draw(st.functions(like=like, returns=st.just(TOKEN)))
    second = data.draw(st.functions(like=first, returns=st.just(b"explicit")))
    assert second((131, "argument")) == b"explicit"
    assert owner.calls == []


@pytest.mark.parametrize("use_partial", [False, True])
@RUN
@given(data=st.data())
def test_callable_truly_unresolved_return_keeps_fallback(use_partial, data):
    owner, _ = owners()
    like = partial(owner.Unknown()) if use_partial else owner.Unknown()
    first = data.draw(st.functions(like=like, returns=st.just(TOKEN)))
    second = data.draw(st.functions(like=first))
    assert second(137) is None


@pytest.mark.parametrize(
    "expression,error", [("1 / 0", ZeroDivisionError), ("()[0]", IndexError)]
)
@RUN
@given(data=st.data())
def test_callable_unrelated_annotation_errors_keep_policy(expression, error, data):
    owner, _ = owners()
    first = data.draw(st.functions(like=owner.Plain(), returns=st.just(TOKEN)))
    first.__annotations__ = {"item": tuple[int, str], "return": expression}
    with pytest.raises(error):
        data.draw(st.functions(like=first))
