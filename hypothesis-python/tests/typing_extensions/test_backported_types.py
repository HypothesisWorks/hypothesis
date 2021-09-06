# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

import collections
from typing import Dict, List, Union

import pytest
from typing_extensions import Annotated, DefaultDict, Literal, NewType, Type, TypedDict

from hypothesis import assume, given, strategies as st
from hypothesis.strategies import from_type


@pytest.mark.parametrize("value", ["dog", b"goldfish", 42, 63.4, -80.5, False])
def test_typing_extensions_Literal(value):
    assert from_type(Literal[value]).example() == value


@given(st.data())
def test_typing_extensions_Literal_nested(data):
    lit = Literal
    values = [
        (lit["hamster", 0], ("hamster", 0)),
        (lit[26, False, "bunny", 130], (26, False, "bunny", 130)),
        (lit[lit[1]], {1}),
        (lit[lit[1], 2], {1, 2}),
        (lit[1, lit[2], 3], {1, 2, 3}),
        (lit[lit[lit[1], lit[2]], lit[lit[3], lit[4]]], {1, 2, 3, 4}),
        # See https://github.com/HypothesisWorks/hypothesis/pull/2886
        (Union[Literal["hamster"], Literal["bunny"]], {"hamster", "bunny"}),
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
