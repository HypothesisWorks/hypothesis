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

import dataclasses
import typing

import pytest

from hypothesis import given, strategies as st
from hypothesis.strategies import from_type
from tests.common.debug import find_any


@given(st.data())
def test_typing_Final(data):
    value = data.draw(from_type(typing.Final[int]))
    assert isinstance(value, int)


@pytest.mark.parametrize("value", ["dog", b"goldfish", 42, 63.4, -80.5, False])
def test_typing_Literal(value):
    assert from_type(typing.Literal[value]).example() == value


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


@pytest.mark.xfail
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


@pytest.mark.xfail
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
