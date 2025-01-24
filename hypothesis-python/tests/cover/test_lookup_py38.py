# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import dataclasses
import re
import typing
from types import SimpleNamespace

import pytest

from hypothesis import example, given, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.internal.reflection import (
    convert_positional_arguments,
    get_pretty_function_description,
)
from hypothesis.strategies import from_type

from tests.common.debug import (
    assert_simple_property,
    check_can_generate_examples,
    find_any,
)
from tests.common.utils import fails_with, temp_registered


@given(st.data())
def test_typing_Final(data):
    value = data.draw(from_type(typing.Final[int]))
    assert isinstance(value, int)


@pytest.mark.parametrize("value", ["dog", b"goldfish", 42, 63.4, -80.5, False])
def test_typing_Literal(value):
    assert_simple_property(from_type(typing.Literal[value]), lambda v: v == value)


@given(st.data())
def test_typing_Literal_nested(data):
    lit = typing.Literal
    values = [
        (lit["hamster", 0], ("hamster", 0)),
        (lit[26, False, "bunny", 130], (26, False, "bunny", 130)),
        (lit[lit[1]], {1}),
        (lit[lit[1], 2], {1, 2}),
        (lit[1, lit[2], 3], {1, 2, 3}),
        (lit[lit[lit[1], lit[2]], lit[lit[3], lit[4]]], {1, 2, 3, 4}),
    ]
    literal_type, flattened_literals = data.draw(st.sampled_from(values))
    assert data.draw(st.from_type(literal_type)) in flattened_literals


class A(typing.TypedDict):
    a: int


@given(from_type(A))
def test_simple_typeddict(value):
    assert type(value) == dict
    assert set(value) == {"a"}
    assert isinstance(value["a"], int)


class B(A, total=False):
    # a is required, b is optional
    b: bool


@given(from_type(B))
def test_typeddict_with_optional(value):
    assert type(value) == dict
    assert set(value).issubset({"a", "b"})
    assert isinstance(value["a"], int)
    if "b" in value:
        assert isinstance(value["b"], bool)


def test_simple_optional_key_is_optional():
    # Optional keys are not currently supported, as PEP-589 leaves no traces
    # at runtime.  See https://github.com/python/cpython/pull/17214
    find_any(from_type(B), lambda d: "b" not in d)


class C(B):
    # a is required, b is optional, c is required again
    c: str


@given(from_type(C))
def test_typeddict_with_optional_then_required_again(value):
    assert type(value) == dict
    assert set(value).issubset({"a", "b", "c"})
    assert isinstance(value["a"], int)
    if "b" in value:
        assert isinstance(value["b"], bool)
    assert isinstance(value["c"], str)


class NestedDict(typing.TypedDict):
    inner: A


@given(from_type(NestedDict))
def test_typeddict_with_nested_value(value):
    assert type(value) == dict
    assert set(value) == {"inner"}
    assert isinstance(value["inner"]["a"], int)


def test_layered_optional_key_is_optional():
    # Optional keys are not currently supported, as PEP-589 leaves no traces
    # at runtime.  See https://github.com/python/cpython/pull/17214
    find_any(from_type(C), lambda d: "b" not in d)


@dataclasses.dataclass()
class Node:
    left: typing.Union["Node", int]
    right: typing.Union["Node", int]


@given(st.builds(Node))
def test_can_resolve_recursive_dataclass(val):
    assert isinstance(val, Node)


def test_can_register_new_type_for_typeddicts():
    sentinel = object()
    with temp_registered(C, st.just(sentinel)):
        assert_simple_property(st.from_type(C), lambda v: v is sentinel)


@pytest.mark.parametrize(
    "lam,source",
    [
        ((lambda a, /, b: a), "lambda a, /, b: a"),
        ((lambda a=None, /, b=None: a), "lambda a=None, /, b=None: a"),
    ],
)
def test_posonly_lambda_formatting(lam, source):
    # Testing posonly lambdas, with and without default values
    assert get_pretty_function_description(lam) == source


def test_does_not_convert_posonly_to_keyword():
    args, kws = convert_positional_arguments(lambda x, /: None, (1,), {})
    assert args
    assert not kws


@given(x=st.booleans())
def test_given_works_with_keyword_only_params(*, x):
    pass


def test_given_works_with_keyword_only_params_some_unbound():
    @given(x=st.booleans())
    def test(*, x, y):
        assert y is None

    test(y=None)


def test_given_works_with_positional_only_params():
    @given(y=st.booleans())
    def test(x, /, y):
        pass

    test(None)


def test_cannot_pass_strategies_by_position_if_there_are_posonly_args():
    @given(st.booleans())
    def test(x, /, y):
        pass

    with pytest.raises(InvalidArgument):
        test(None)


@fails_with(InvalidArgument)
@given(st.booleans())
def test_cannot_pass_strategies_for_posonly_args(x, /):
    pass


@given(y=st.booleans())
def has_posonly_args(x, /, y):
    pass


def test_example_argument_validation():
    example(y=None)(has_posonly_args)(1)  # Basic case is OK

    with pytest.raises(
        InvalidArgument,
        match=re.escape(
            "Cannot pass positional arguments to @example() when decorating "
            "a test function which has positional-only parameters."
        ),
    ):
        example(None)(has_posonly_args)(1)

    with pytest.raises(
        InvalidArgument,
        match=re.escape(
            "Inconsistent args: @given() got strategies for 'y', "
            "but @example() got arguments for 'x'"
        ),
    ):
        example(x=None)(has_posonly_args)(1)


class FooProtocol(typing.Protocol):
    def frozzle(self, x):
        pass


class BarProtocol(typing.Protocol):
    def bazzle(self, y):
        pass


@given(st.data())
def test_can_resolve_registered_protocol(data):
    with temp_registered(
        FooProtocol,
        st.builds(SimpleNamespace, frozzle=st.functions(like=lambda x: ...)),
    ):
        obj = data.draw(st.from_type(FooProtocol))
    assert obj.frozzle(x=1) is None


def test_cannot_resolve_un_registered_protocol():
    msg = "Instance and class checks can only be used with @runtime_checkable protocols"
    with pytest.raises(TypeError, match=msg):
        check_can_generate_examples(st.from_type(BarProtocol))
