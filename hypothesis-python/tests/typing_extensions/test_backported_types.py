# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import collections
from typing import Annotated, Callable, DefaultDict, NewType, Union

import pytest
import typing_extensions
from typing_extensions import (
    Concatenate,
    LiteralString,
    NotRequired,
    ParamSpec,
    ReadOnly,
    Required,
    TypedDict,
    TypeGuard,
    TypeIs,
)

from hypothesis import HealthCheck, assume, given, settings, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.strategies import from_type
from hypothesis.strategies._internal.types import NON_RUNTIME_TYPES

from tests.common.debug import (
    assert_all_examples,
    assert_simple_property,
    check_can_generate_examples,
    find_any,
)

# See also nocover/test_type_lookup.py


@pytest.mark.parametrize("value", ["dog", b"goldfish", 42, 63.4, -80.5, False])
def test_typing_extensions_Literal(value):
    assert_simple_property(
        from_type(typing_extensions.Literal[value]), lambda v: v == value
    )


@given(st.data())
def test_typing_extensions_Literal_nested(data):
    lit = typing_extensions.Literal
    values = [
        (lit["hamster", 0], ("hamster", 0)),
        (lit[26, False, "bunny", 130], (26, False, "bunny", 130)),
        (lit[lit[1]], {1}),
        (lit[lit[1], 2], {1, 2}),
        (lit[1, lit[2], 3], {1, 2, 3}),
        (lit[lit[lit[1], lit[2]], lit[lit[3], lit[4]]], {1, 2, 3, 4}),
        # See https://github.com/HypothesisWorks/hypothesis/pull/2886
        (Union[lit["hamster"], lit["bunny"]], {"hamster", "bunny"}),  # noqa
        (Union[lit[lit[1], lit[2]], lit[lit[3], lit[4]]], {1, 2, 3, 4}),
    ]
    literal_type, flattened_literals = data.draw(st.sampled_from(values))
    assert data.draw(st.from_type(literal_type)) in flattened_literals


class A(TypedDict):
    a: int


@given(from_type(A))
def test_simple_typeddict(value):
    assert type(value) == dict
    assert set(value) == {"a"}
    assert isinstance(value["a"], int)


def test_typing_extensions_Type_int():
    assert_simple_property(from_type(type[int]), lambda v: v is int)


@given(from_type(Union[type[str], type[list]]))
def test_typing_extensions_Type_Union(ex):
    assert ex in (str, list)


def test_resolves_NewType():
    typ = NewType("T", int)
    nested = NewType("NestedT", typ)
    uni = NewType("UnionT", Union[int, None])
    assert_simple_property(from_type(typ), lambda x: isinstance(x, int))
    assert_simple_property(from_type(nested), lambda x: isinstance(x, int))
    assert_simple_property(from_type(uni), lambda x: isinstance(x, (int, type(None))))
    find_any(from_type(uni), lambda x: isinstance(x, int))
    find_any(from_type(uni), lambda x: isinstance(x, type(None)))


@given(from_type(DefaultDict[int, int]))
def test_defaultdict(ex):
    assert isinstance(ex, collections.defaultdict)
    assume(ex)
    assert all(isinstance(elem, int) for elem in ex)
    assert all(isinstance(elem, int) for elem in ex.values())


@pytest.mark.parametrize("non_runtime_type", NON_RUNTIME_TYPES)
def test_non_runtime_type_cannot_be_resolved(non_runtime_type):
    strategy = st.from_type(non_runtime_type)
    with pytest.raises(
        InvalidArgument, match="there is no such thing as a runtime instance"
    ):
        check_can_generate_examples(strategy)


@pytest.mark.parametrize("non_runtime_type", NON_RUNTIME_TYPES)
def test_non_runtime_type_cannot_be_registered(non_runtime_type):
    with pytest.raises(
        InvalidArgument, match="there is no such thing as a runtime instance"
    ):
        st.register_type_strategy(non_runtime_type, st.none())


def test_callable_with_concatenate():
    P = ParamSpec("P")
    func_type = Callable[Concatenate[int, P], None]
    strategy = st.from_type(func_type)
    with pytest.raises(
        InvalidArgument,
        match="Hypothesis can't yet construct a strategy for instances of a Callable type",
    ):
        check_can_generate_examples(strategy)

    with pytest.raises(InvalidArgument, match="Cannot register generic type"):
        st.register_type_strategy(func_type, st.none())


def test_callable_with_paramspec():
    P = ParamSpec("P")
    func_type = Callable[P, None]
    strategy = st.from_type(func_type)
    with pytest.raises(
        InvalidArgument,
        match="Hypothesis can't yet construct a strategy for instances of a Callable type",
    ):
        check_can_generate_examples(strategy)

    with pytest.raises(InvalidArgument, match="Cannot register generic type"):
        st.register_type_strategy(func_type, st.none())


@pytest.mark.parametrize("typ", [TypeGuard, TypeIs])
def test_callable_return_typegard_type(typ):
    strategy = st.from_type(Callable[[], typ[int]])
    with pytest.raises(
        InvalidArgument,
        match="Hypothesis cannot yet construct a strategy for callables "
        "which are PEP-647 TypeGuards or PEP-742 TypeIs",
    ):
        check_can_generate_examples(strategy)

    with pytest.raises(InvalidArgument, match="Cannot register generic type"):
        st.register_type_strategy(Callable[[], typ[int]], st.none())


class Movie(TypedDict):  # implicitly total=True
    title: str
    year: NotRequired[int]


@given(from_type(Movie))
def test_typeddict_not_required(value):
    assert type(value) == dict
    assert set(value).issubset({"title", "year"})
    assert isinstance(value["title"], str)
    if "year" in value:
        assert isinstance(value["year"], int)


def test_typeddict_not_required_can_skip():
    find_any(from_type(Movie), lambda movie: "year" not in movie)


class OtherMovie(TypedDict, total=False):
    title: Required[str]
    year: int


@given(from_type(OtherMovie))
def test_typeddict_required(value):
    assert type(value) == dict
    assert set(value).issubset({"title", "year"})
    assert isinstance(value["title"], str)
    if "year" in value:
        assert isinstance(value["year"], int)


def test_typeddict_required_must_have():
    assert_all_examples(from_type(OtherMovie), lambda movie: "title" in movie)


class Story(TypedDict, total=True):
    author: str


class Book(Story, total=False):
    pages: int


class Novel(Book):
    genre: Required[str]
    rating: NotRequired[str]


@pytest.mark.parametrize(
    "check,condition",
    [
        pytest.param(
            assert_all_examples,
            lambda novel: "author" in novel,
            id="author-is-required",
        ),
        pytest.param(
            assert_all_examples, lambda novel: "genre" in novel, id="genre-is-required"
        ),
        pytest.param(
            find_any, lambda novel: "pages" in novel, id="pages-may-be-present"
        ),
        pytest.param(
            find_any, lambda novel: "pages" not in novel, id="pages-may-be-absent"
        ),
        pytest.param(
            find_any, lambda novel: "rating" in novel, id="rating-may-be-present"
        ),
        pytest.param(
            find_any, lambda novel: "rating" not in novel, id="rating-may-be-absent"
        ),
    ],
)
def test_required_and_not_required_keys(check, condition):
    check(from_type(Novel), condition)


class DeeplyNestedQualifiers(TypedDict):
    a: ReadOnly[Required[int]]
    b: NotRequired[Annotated[ReadOnly[int], "metadata"]]
    c: Annotated[ReadOnly[NotRequired[str]], "metadata"]


@pytest.mark.parametrize(
    "check,condition",
    [
        pytest.param(
            assert_all_examples,
            lambda novel: "a" in novel,
            id="a-is-required",
        ),
        pytest.param(find_any, lambda novel: "b" in novel, id="b-may-be-present"),
        pytest.param(find_any, lambda novel: "b" not in novel, id="b-may-be-absent"),
        pytest.param(find_any, lambda novel: "c" in novel, id="c-may-be-present"),
        pytest.param(find_any, lambda novel: "c" not in novel, id="c-may-be-absent"),
    ],
)
def test_required_and_not_required_keys_deeply_nested(check, condition):
    check(from_type(DeeplyNestedQualifiers), condition)


def test_typeddict_error_msg():
    with pytest.raises(TypeError, match="is not valid as type argument"):

        class Foo(TypedDict):
            attr: Required

    with pytest.raises(TypeError, match="is not valid as type argument"):

        class Bar(TypedDict):
            attr: NotRequired

    with pytest.raises(TypeError, match="is not valid as type argument"):

        class Baz(TypedDict):
            attr: ReadOnly


def test_literal_string_is_just_a_string():
    assert_all_examples(from_type(LiteralString), lambda thing: isinstance(thing, str))


class Foo:
    def __init__(self, x):
        pass


class Bar(Foo):
    pass


class Baz(Foo):
    pass


st.register_type_strategy(Bar, st.builds(Bar, st.integers()))
st.register_type_strategy(Baz, st.builds(Baz, st.integers()))

T = typing_extensions.TypeVar("T")
T_int = typing_extensions.TypeVar("T_int", bound=int)


@pytest.mark.parametrize(
    "var,expected",
    [
        (typing_extensions.TypeVar("V"), object),
        # Bound:
        (typing_extensions.TypeVar("V", bound=int), int),
        (typing_extensions.TypeVar("V", bound=Foo), (Bar, Baz)),
        (typing_extensions.TypeVar("V", bound=Union[int, str]), (int, str)),
        # Constraints:
        (typing_extensions.TypeVar("V", int, str), (int, str)),
        # Default:
        (typing_extensions.TypeVar("V", default=int), int),
        (typing_extensions.TypeVar("V", default=T), object),
        (typing_extensions.TypeVar("V", default=Foo), (Bar, Baz)),
        (typing_extensions.TypeVar("V", default=Union[int, str]), (int, str)),
        (typing_extensions.TypeVar("V", default=T_int), int),
        (typing_extensions.TypeVar("V", default=T_int, bound=int), int),
        (typing_extensions.TypeVar("V", int, str, default=int), (int, str)),
        # This case is not correct from typing's perspective, but its not
        # our job to very this, static type-checkers should do that:
        (typing_extensions.TypeVar("V", default=T_int, bound=str), (int, str)),
    ],
)
@settings(suppress_health_check=[HealthCheck.too_slow])
@given(data=st.data())
def test_typevar_type_is_consistent(data, var, expected):
    strat = st.from_type(var)
    v1 = data.draw(strat)
    v2 = data.draw(strat)
    assume(v1 != v2)  # Values may vary, just not types
    assert type(v1) == type(v2)
    assert isinstance(v1, expected)
