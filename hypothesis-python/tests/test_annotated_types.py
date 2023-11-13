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

import pytest

from hypothesis import strategies as st
from hypothesis.errors import HypothesisWarning, ResolutionFailed
from hypothesis.strategies._internal.lazy import unwrap_strategies
from hypothesis.strategies._internal.strategies import FilteredStrategy

try:
    from typing import Annotated  # new in Python 3.9

    import annotated_types as at
except ImportError:
    pytest.skip()


def test_strategy_priority_over_constraints():
    expected_strategy = st.SearchStrategy()

    strategy = st.from_type(Annotated[int, expected_strategy, at.Gt(1)])
    assert strategy is expected_strategy


def test_invalid_annotated_type():
    with pytest.raises(ResolutionFailed):
        st.from_type(Annotated[None, "dummy", Annotated[int, "dummy"]]).example()


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
        st.from_type(t).example()


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
