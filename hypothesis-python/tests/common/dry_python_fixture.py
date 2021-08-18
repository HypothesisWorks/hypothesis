from abc import abstractmethod
from typing import Any, Callable, Generic, NoReturn, TypeVar

from typing_extensions import final

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


class SupportsKindN(
    KindN[_InstanceType, _TypeArgType1, _TypeArgType2, _TypeArgType3],
):
    __getattr__: None  # type: ignore


SupportsKind1 = SupportsKindN[
    _InstanceType,
    _TypeArgType1,
    NoReturn,
    NoReturn,
]


_FirstType = TypeVar("_FirstType")
_SecondType = TypeVar("_SecondType")
_ThirdType = TypeVar("_ThirdType")
_UpdatedType = TypeVar("_UpdatedType")

_MappableType = TypeVar("_MappableType", bound="MappableN")

# Used in laws:
_NewType1 = TypeVar("_NewType1")
_NewType2 = TypeVar("_NewType2")


def identity(instance: _FirstType) -> _FirstType:
    return instance


@final
class _LawSpec(object):
    """Mappable or functor laws."""

    # This type intentionally misses `associative_law`,
    # it is not required for tests

    @staticmethod
    def identity_law(
        mappable: "MappableN[_FirstType, _SecondType, _ThirdType]",
    ) -> None:
        """Mapping identity over a value must return the value unchanged."""
        assert mappable.map(identity) == mappable


class Lawful(Generic[_NewType1]):
    """This type defines law-related operations."""


class MappableN(
    Generic[_FirstType, _SecondType, _ThirdType],
    Lawful["MappableN[_FirstType, _SecondType, _ThirdType]"],
):
    """Behaves like a functor."""

    laws = (_LawSpec.identity_law,)

    @abstractmethod
    def map(
        self: _MappableType,
        function: Callable[[_FirstType], _UpdatedType],
    ) -> KindN[_MappableType, _UpdatedType, _SecondType, _ThirdType]:
        """Allows to run a pure function over a container."""


Mappable1 = MappableN[_FirstType, NoReturn, NoReturn]
