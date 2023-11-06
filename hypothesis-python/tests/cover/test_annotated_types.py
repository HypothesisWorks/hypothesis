# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from typing import Annotated

import pytest

from hypothesis import strategies as st
from hypothesis.errors import HypothesisWarning, ResolutionFailed
from hypothesis.strategies._internal.strategies import FilteredStrategy

try:
    import annotated_types as at
except ImportError:
    at = None

pytestmark = pytest.mark.skipif(
    at is None, reason="Requires annotated_types to be installed."
)


def test_strategy_priority_over_constraints():
    expected_strategy = st.SearchStrategy()

    strategy = st.from_type(Annotated[int, expected_strategy, at.Gt(1)])
    assert strategy is expected_strategy


def test_invalid_annotated_type():
    with pytest.raises(ResolutionFailed):
        st.from_type(Annotated[None, "dummy", Annotated[int, "dummy"]])


@pytest.mark.parametrize(
    "unsupported_constraints,message",
    [
        (
            (at.Timezone(None),),
            "Timezone(tz=None) is currently not supported and will be ignored.",
        ),
        (
            (at.MultipleOf(1),),
            "MultipleOf(multiple_of=1) is currently not supported and will be ignored.",
        ),
        (
            (at.Timezone(None), at.MultipleOf(1)),
            "Timezone(tz=None), MultipleOf(multiple_of=1) are currently not supported and will be ignored.",
        ),
    ],
)
def test_unsupported_constraints(unsupported_constraints, message):
    with pytest.warns(HypothesisWarning, match=message):
        # Calling __class_getitem__ as Annotated[int, *args] is not supported <3.11
        st.from_type(Annotated.__class_getitem__((int, *unsupported_constraints)))


def test_unknown_constraint(capsys):
    class Unknown(at.BaseMetadata):
        def __str__(self):
            return "unknown"

    st.from_type(Annotated[int, Unknown()])

    captured = capsys.readouterr()
    assert (
        captured.out
        == "WARNING: the following constraints are unknown and will be ignored: unknown."
    )


@pytest.mark.parametrize(
    "annotated_type,expected_strategy_repr",
    [
        (Annotated[int, at.Gt(1)], "integers(min_value=2)"),
        (Annotated[int, at.Ge(1)], "integers(min_value=1)"),
        (Annotated[int, at.Lt(1)], "integers(max_value=0)"),
        (Annotated[int, at.Le(1)], "integers(max_value=1)"),
        (Annotated[int, at.Interval(ge=1, le=3)], "integers(min_value=1, max_value=3)"),
        (Annotated[int, at.Interval(ge=1), at.Ge(2)], "integers(min_value=2)"),
    ],
)
def test_annotated_type_int(annotated_type, expected_strategy_repr):
    strategy = st.from_type(annotated_type)
    assert repr(strategy.wrapped_strategy) == expected_strategy_repr


def test_predicate_constraint():

    def func(_):
        return True

    strategy = st.from_type(Annotated[int, at.Predicate(func)])
    assert isinstance(strategy, FilteredStrategy)
    assert strategy.flat_conditions == (func,)
