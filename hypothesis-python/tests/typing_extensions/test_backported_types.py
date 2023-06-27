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
from typing import Callable, DefaultDict, Dict, List, NewType, Type, Union

import pytest
import typing_extensions
from typing_extensions import (
    Annotated,
    Concatenate,
    NotRequired,
    ParamSpec,
    Required,
    TypedDict,
    TypeGuard,
)

from hypothesis import assume, given, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.strategies import from_type
from hypothesis.strategies._internal.types import NON_RUNTIME_TYPES

from tests.common.debug import assert_all_examples, find_any

# See also nocover/test_type_lookup.py


@pytest.mark.parametrize("value", ["dog", b"goldfish", 42, 63.4, -80.5, False])
def test_typing_extensions_Literal(value):
    assert from_type(typing_extensions.Literal[value]).example() == value


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
    assert from_type(Type[int]).example() is int


@given(from_type(Type[Union[str, list]]))
def test_typing_extensions_Type_Union(ex):
    assert ex in (str, list)


def test_resolves_NewType():
    typ = NewType("T", int)
    nested = NewType("NestedT", typ)
    uni = NewType("UnionT", Union[int, None])
    assert isinstance(from_type(typ).example(), int)
    assert isinstance(from_type(nested).example(), int)
    assert isinstance(from_type(uni).example(), (int, type(None)))


@given(from_type(DefaultDict[int, int]))
def test_defaultdict(ex):
    assert isinstance(ex, collections.defaultdict)
    assume(ex)
    assert all(isinstance(elem, int) for elem in ex)
    assert all(isinstance(elem, int) for elem in ex.values())


@pytest.mark.parametrize(
    "annotated_type,expected_strategy_repr",
    [
        (Annotated[int, "foo"], "integers()"),
        (Annotated[List[float], "foo"], "lists(floats())"),
        (Annotated[Annotated[str, "foo"], "bar"], "text()"),
        (
            Annotated[Annotated[List[Dict[str, bool]], "foo"], "bar"],
            "lists(dictionaries(keys=text(), values=booleans()))",
        ),
    ],
)
def test_typing_extensions_Annotated(annotated_type, expected_strategy_repr):
    assert repr(st.from_type(annotated_type)) == expected_strategy_repr


PositiveInt = Annotated[int, st.integers(min_value=1)]
MoreThenTenInt = Annotated[PositiveInt, st.integers(min_value=10 + 1)]
WithTwoStrategies = Annotated[int, st.integers(), st.none()]
ExtraAnnotationNoStrategy = Annotated[PositiveInt, "metadata"]


def arg_positive(x: PositiveInt):
    assert x > 0


def arg_more_than_ten(x: MoreThenTenInt):
    assert x > 10


@given(st.data())
def test_annotated_positive_int(data):
    data.draw(st.builds(arg_positive))


@given(st.data())
def test_annotated_more_than_ten(data):
    data.draw(st.builds(arg_more_than_ten))


@given(st.data())
def test_annotated_with_two_strategies(data):
    assert data.draw(st.from_type(WithTwoStrategies)) is None


@given(st.data())
def test_annotated_extra_metadata(data):
    assert data.draw(st.from_type(ExtraAnnotationNoStrategy)) > 0


@pytest.mark.parametrize("non_runtime_type", NON_RUNTIME_TYPES)
def test_non_runtime_type_cannot_be_resolved(non_runtime_type):
    strategy = st.from_type(non_runtime_type)
    with pytest.raises(
        InvalidArgument, match="there is no such thing as a runtime instance"
    ):
        strategy.example()


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
        strategy.example()

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
        strategy.example()

    with pytest.raises(InvalidArgument, match="Cannot register generic type"):
        st.register_type_strategy(func_type, st.none())


def test_callable_return_typegard_type():
    strategy = st.from_type(Callable[[], TypeGuard[int]])
    with pytest.raises(
        InvalidArgument,
        match="Hypothesis cannot yet construct a strategy for callables "
        "which are PEP-647 TypeGuards",
    ):
        strategy.example()

    with pytest.raises(InvalidArgument, match="Cannot register generic type"):
        st.register_type_strategy(Callable[[], TypeGuard[int]], st.none())


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


def test_typeddict_error_msg():
    with pytest.raises(TypeError, match="is not valid as type argument"):

        class Foo(TypedDict):
            attr: Required

    with pytest.raises(TypeError, match="is not valid as type argument"):

        class Bar(TypedDict):
            attr: NotRequired
