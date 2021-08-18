from abc import abstractmethod
from typing import Generic, NoReturn, TypeVar

import pytest
from hypothesis.errors import ResolutionFailed
from tests.common.utils import temp_registered

from hypothesis import given
from hypothesis import strategies as st

# Primitives:
# ===========

_InstanceType = TypeVar("_InstanceType", covariant=True)
_TypeArgType1 = TypeVar("_TypeArgType1", covariant=True)
_TypeArgType2 = TypeVar("_TypeArgType2", covariant=True)
_TypeArgType3 = TypeVar("_TypeArgType3", covariant=True)


class KindN(
    Generic[_InstanceType, _TypeArgType1, _TypeArgType2, _TypeArgType3],
):
    pass


_FirstType = TypeVar("_FirstType")
_SecondType = TypeVar("_SecondType")
_ThirdType = TypeVar("_ThirdType")
_UpdatedType = TypeVar("_UpdatedType")

_LawType = TypeVar("_LawType")


class Lawful(Generic[_LawType]):
    """This type defines law-related operations."""


class MappableN(
    Generic[_FirstType, _SecondType, _ThirdType],
    Lawful["MappableN[_FirstType, _SecondType, _ThirdType]"],
):
    """Behaves like a functor."""


# End definition:
# ===============

_ValueType = TypeVar("_ValueType")
_NewValueType = TypeVar("_NewValueType")


class MyFunctor(
    KindN["MyFunctor", _ValueType, NoReturn, NoReturn],
    MappableN[_ValueType, NoReturn, NoReturn],
):
    def __init__(self, inner_value: _ValueType) -> None:
        self.inner_value = inner_value


# Testing part:
# =============


def target_func(
    mappable: "MappableN[_FirstType, _SecondType, _ThirdType]",
) -> bool:
    return isinstance(mappable, MappableN)


@pytest.mark.xfail(raises=ResolutionFailed)
@given(st.data())
def test_my_mappable(source: st.DataObject) -> None:
    """
    Checks that complex

    Regression to https://github.com/HypothesisWorks/hypothesis/issues/3060
    """
    # In `returns` we register all types in `__mro__`
    # to be this exact type at the moment. But here, we ony need `Mappable`.
    # Current `__mro__` is `MyFunctor / Kind / Mappable`:
    with temp_registered(
        MyFunctor.__mro__[2],
        st.builds(MyFunctor),
    ):
        assert source.draw(st.builds(target_func)) is True
