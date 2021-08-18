from typing import Callable, TypeVar

import pytest
from hypothesis.errors import ResolutionFailed
from tests.common.dry_python_fixture import Mappable1, SupportsKind1
from tests.common.utils import temp_registered

from hypothesis import given
from hypothesis import strategies as st

# End definition:
# ===============

_ValueType = TypeVar("_ValueType")
_NewValueType = TypeVar("_NewValueType")


class MyFunctor(SupportsKind1["MyFunctor", _ValueType], Mappable1[_ValueType]):
    def __init__(self, inner_value: _ValueType) -> None:
        self.inner_value = inner_value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, MyFunctor) and self.inner_value == other.inner_value

    def map(
        self,
        function: Callable[[_ValueType], _NewValueType],
    ) -> "My[_NewValueType]":
        return MyFunctor(function(self.inner_value))


# Testing part:
# =============

# The same logic we have in:
# returns/contrib/hypothesis/laws.py#L97
def typevar_factory(thing):
    from hypothesis.strategies._internal import types

    type_strategies = [
        types.resolve_TypeVar(thing),
    ]
    return st.one_of(type_strategies).filter(
        lambda inner: inner == inner,
    )


@pytest.mark.xfail(raises=ResolutionFailed)
@given(st.data())
def test_my_mappable(source: st.DataObject) -> None:
    """
    Checks that complex

    Regression to https://github.com/HypothesisWorks/hypothesis/issues/3060
    """
    # In `returns` we register all types in `mro`
    # to be this exact type at the moment.
    # Current `__mro__` is `MyFunctor / SupportsKind / Kind / Mappable`:
    with temp_registered(TypeVar, typevar_factory):
        with temp_registered(
            MyFunctor.__mro__[0], st.builds(MyFunctor)
        ), temp_registered(MyFunctor.__mro__[1], st.builds(MyFunctor)), temp_registered(
            MyFunctor.__mro__[2],
            st.builds(MyFunctor),
        ), temp_registered(
            MyFunctor.__mro__[3], st.builds(MyFunctor)
        ):
            source.draw(st.builds(MyFunctor.laws[0]))
