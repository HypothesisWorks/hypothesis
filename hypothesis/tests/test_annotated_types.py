# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import datetime as dt
import re
import sys
import zoneinfo
from typing import Annotated, TypeVar

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import HypothesisWarning, InvalidArgument, ResolutionFailed
from hypothesis.strategies._internal.lazy import unwrap_strategies
from hypothesis.strategies._internal.strategies import FilteredStrategy
from hypothesis.strategies._internal.types import _get_constraints

from tests.common.debug import (
    assert_all_examples,
    assert_simple_property,
    check_can_generate_examples,
)

try:
    import annotated_types as at
except ImportError:
    pytest.skip(allow_module_level=True)


def test_strategy_priority_over_constraints():
    expected_strategy = st.SearchStrategy()

    strategy = st.from_type(Annotated[int, expected_strategy, at.Gt(1)])
    assert strategy is expected_strategy


def test_invalid_annotated_type():
    msg = re.escape("Did you mean `Annotated[str | int, 'dummy']`?")
    with pytest.raises(ResolutionFailed, match=f".*{msg}$"):
        check_can_generate_examples(
            st.from_type(Annotated[str, "dummy", Annotated[int, "dummy"]])
        )


@pytest.mark.parametrize(
    "unsupported_constraints,message",
    [
        ((at.Timezone(None),), "Ignoring unsupported Timezone(tz=None)"),
        ((at.MultipleOf(1),), "Ignoring unsupported MultipleOf(multiple_of=1)"),
        (
            (at.Timezone(None), at.MultipleOf(1)),
            "Ignoring unsupported Timezone(tz=None), MultipleOf(multiple_of=1)",
        ),
    ],
)
def test_unsupported_constraints(unsupported_constraints, message):
    if sys.version_info >= (3, 11):
        # This is the preferred format, but also a SyntaxError on Python <= 3.10
        t = eval("Annotated[int, *unsupported_constraints]", globals(), locals())
    else:
        t = Annotated.__class_getitem__((int, *unsupported_constraints))
    with pytest.warns(HypothesisWarning, match=re.escape(message)):
        check_can_generate_examples(st.from_type(t))


@pytest.mark.parametrize(
    "annotated_type,expected_strategy_repr",
    [
        (Annotated[int, at.Gt(1)], "integers(min_value=2)"),
        (Annotated[int, at.Ge(1)], "integers(min_value=1)"),
        (Annotated[int, at.Lt(1)], "integers(max_value=0)"),
        (Annotated[int, at.Le(1)], "integers(max_value=1)"),
        (Annotated[int, at.Interval(ge=1, le=3)], "integers(1, 3)"),
        (Annotated[int, at.Interval(ge=1), at.Ge(2)], "integers(min_value=2)"),
    ],
)
def test_annotated_type_int(annotated_type, expected_strategy_repr):
    strategy = unwrap_strategies(st.from_type(annotated_type))
    assert repr(strategy) == expected_strategy_repr


@pytest.mark.parametrize("type_", [dt.datetime, dt.time])
@pytest.mark.parametrize(
    "tz,predicate",
    [
        (None, lambda value: value.tzinfo is None),
        (..., lambda value: value.tzinfo is not None),
        (
            "Europe/London",
            lambda value: value.tzinfo == zoneinfo.ZoneInfo("Europe/London"),
        ),
        (dt.timezone.utc, lambda value: value.tzinfo is dt.timezone.utc),
    ],
)
def test_timezone_constraint(type_, tz, predicate):
    assert_all_examples(st.from_type(Annotated[type_, at.Timezone(tz)]), predicate)


def test_invalid_timezone_value():
    with pytest.raises(InvalidArgument, match="Cannot resolve Timezone"):
        check_can_generate_examples(
            st.from_type(Annotated[dt.datetime, at.Timezone(42)])
        )


def test_timezone_constraint_combines_with_others():
    epoch = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
    strategy = st.from_type(Annotated[dt.datetime, at.Timezone(...), at.Ge(epoch)])
    assert_all_examples(
        strategy, lambda value: value.tzinfo is not None and value >= epoch
    )


def test_generic_alias_in_metadata_suggests_subscripting():
    with pytest.raises(ResolutionFailed) as excinfo:
        check_can_generate_examples(st.from_type(Annotated[str, at.LowerCase]))
    assert "Did you mean `Annotated[str, Predicate(str.islower)]`?" in str(
        excinfo.value
    )
    assert "try `LowerCase[str]`" in str(excinfo.value)


def test_unknown_generic_alias_in_metadata_error():
    T = TypeVar("T")
    Positive = Annotated[T, at.Gt(0)]
    with pytest.raises(ResolutionFailed) as excinfo:
        check_can_generate_examples(st.from_type(Annotated[int, Positive]))
    assert "Did you mean `Annotated[int, Gt(gt=0)]`?" in str(excinfo.value)
    assert "subscripted with the type" in str(excinfo.value)


def test_predicate_constraint():
    def func(_):
        return True

    strategy = unwrap_strategies(st.from_type(Annotated[int, at.Predicate(func)]))
    assert isinstance(strategy, FilteredStrategy)
    assert strategy.flat_conditions == (func,)


class MyCollection:
    def __init__(self, values: list[int]) -> None:
        self._values = values

    def __len__(self) -> int:
        return len(self._values)


@pytest.mark.parametrize("lo", [0, 1])
@pytest.mark.parametrize("hi", [None, 10])
@pytest.mark.parametrize("type_", [list[int], set[int], MyCollection])
@given(data=st.data())
def test_collection_sizes(data, lo, hi, type_):
    print(f"{type_=} {lo=} {hi=}")
    assert lo < (hi or 11)
    t = Annotated[type_, at.Len(min_length=lo, max_length=hi)]
    s = st.from_type(t)
    value = data.draw(s)
    assert lo is None or lo <= len(value)
    assert hi is None or len(value) <= hi


@given(st.data())
def test_collection_size_from_slice(data):
    t = Annotated[MyCollection, "we just ignore this", slice(1, 10)]
    value = data.draw(st.from_type(t))
    assert 1 <= len(value) <= 10


def test_unhashable_annotated_metadata():
    t = Annotated[int, {"key": "value"}]
    assert_simple_property(st.from_type(t), lambda x: isinstance(x, int))


class GroupedStuff:
    __is_annotated_types_grouped_metadata__ = True

    def __init__(self, *args) -> None:
        self._args = args

    def __iter__(self):
        return iter(self._args)

    def __repr__(self) -> str:
        return f"GroupedStuff({', '.join(map(repr, self._args))})"


def test_flattens_grouped_metadata():
    grp = GroupedStuff(GroupedStuff(GroupedStuff(at.Len(min_length=1, max_length=5))))
    constraints = list(_get_constraints(grp))
    assert constraints == [at.MinLen(1), at.MaxLen(5)]


try:
    # we can drop this ugly code when Python 3.10 reaches EOL
    from typing import NotRequired, TypedDict
except ImportError:
    pass
else:

    class TypedDictWithAnnotations(TypedDict):
        x: Annotated[int, at.Ge(0)]
        y: Annotated[NotRequired[int], at.Ge(0)]
        z: NotRequired[Annotated[int, at.Ge(0)]]

    @given(st.from_type(TypedDictWithAnnotations))
    def test_typeddict_with_annotated_constraints(value):
        assert value["x"] >= 0
        assert value.get("y", 0) >= 0
        assert value.get("z", 0) >= 0
