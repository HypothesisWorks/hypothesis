# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re
import sys
from typing import Annotated

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import HypothesisWarning, ResolutionFailed
from hypothesis.strategies._internal.lazy import unwrap_strategies
from hypothesis.strategies._internal.strategies import FilteredStrategy
from hypothesis.strategies._internal.types import _get_constraints

from tests.common.debug import check_can_generate_examples

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
