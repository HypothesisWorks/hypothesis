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
import sys
import typing

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument

from tests.common.debug import assert_all_examples, find_any
from tests.common.utils import temp_registered


@pytest.mark.parametrize(
    "annotated_type,expected_strategy_repr",
    [
        (typing.Annotated[int, "foo"], "integers()"),
        (typing.Annotated[typing.List[float], "foo"], "lists(floats())"),
        (typing.Annotated[typing.Annotated[str, "foo"], "bar"], "text()"),
        (
            typing.Annotated[
                typing.Annotated[typing.List[typing.Dict[str, bool]], "foo"], "bar"
            ],
            "lists(dictionaries(keys=text(), values=booleans()))",
        ),
    ],
)
def test_typing_Annotated(annotated_type, expected_strategy_repr):
    assert repr(st.from_type(annotated_type)) == expected_strategy_repr


PositiveInt = typing.Annotated[int, st.integers(min_value=1)]
MoreThenTenInt = typing.Annotated[PositiveInt, st.integers(min_value=10 + 1)]
WithTwoStrategies = typing.Annotated[int, st.integers(), st.none()]
ExtraAnnotationNoStrategy = typing.Annotated[PositiveInt, "metadata"]


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


@dataclasses.dataclass
class User:
    id: int
    following: list["User"]  # works with typing.List


@pytest.mark.skipif(sys.version_info[:2] >= (3, 11), reason="works in new Pythons")
def test_string_forward_ref_message():
    # See https://github.com/HypothesisWorks/hypothesis/issues/3016
    s = st.builds(User)
    with pytest.raises(InvalidArgument, match="`from __future__ import annotations`"):
        s.example()


def test_issue_3080():
    # Check for https://github.com/HypothesisWorks/hypothesis/issues/3080
    s = st.from_type(typing.Union[list[int], int])
    find_any(s, lambda x: isinstance(x, int))
    find_any(s, lambda x: isinstance(x, list))


@dataclasses.dataclass
class TypingTuple:
    a: dict[typing.Tuple[int, int], str]


@dataclasses.dataclass
class BuiltinTuple:
    a: dict[tuple[int, int], str]


TestDataClass = typing.Union[TypingTuple, BuiltinTuple]


@pytest.mark.parametrize("data_class", [TypingTuple, BuiltinTuple])
@given(data=st.data())
def test_from_type_with_tuple_works(data, data_class: TestDataClass):
    value: TestDataClass = data.draw(st.from_type(data_class))
    assert len(value.a) >= 0


def _shorter_lists(list_type):
    return st.lists(st.from_type(*typing.get_args(list_type)), max_size=2)


def test_can_register_builtin_list():
    # Regression test for https://github.com/HypothesisWorks/hypothesis/issues/3635
    with temp_registered(list, _shorter_lists):
        assert_all_examples(
            st.from_type(list[int]),
            lambda ls: len(ls) <= 2 and {type(x) for x in ls}.issubset({int}),
        )
