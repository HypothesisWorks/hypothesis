# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from typing import Generic, TypeVar

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import ResolutionFailed

from tests.common.debug import check_can_generate_examples, find_any
from tests.common.utils import temp_registered

# Primitives:
# ===========

_InstanceType = TypeVar("_InstanceType", covariant=True)
_TypeArgType1 = TypeVar("_TypeArgType1", covariant=True)
_FirstType = TypeVar("_FirstType")
_LawType = TypeVar("_LawType")


class KindN(Generic[_InstanceType, _TypeArgType1]):
    pass


class Lawful(Generic[_LawType]):
    """This type defines law-related operations."""


class MappableN(Generic[_FirstType], Lawful["MappableN[_FirstType]"]):
    """Behaves like a functor."""


# End definition:
# ===============

_ValueType = TypeVar("_ValueType")


class MyFunctor(KindN["MyFunctor", _ValueType], MappableN[_ValueType]):
    def __init__(self, inner_value: _ValueType) -> None:
        self.inner_value = inner_value


# Testing part:
# =============


def target_func(mappable: "MappableN[_FirstType]") -> bool:
    return isinstance(mappable, MappableN)


@given(st.data())
def test_my_mappable(source: st.DataObject) -> None:
    """
    Checks that complex types with multiple inheritance levels and strings are fine.

    Regression test for https://github.com/HypothesisWorks/hypothesis/issues/3060
    """
    # In `returns` we register all types in `__mro__`
    # to be this exact type at the moment. But here, we only need `Mappable`.
    # Current `__mro__` is `MyFunctor / Kind / Mappable`:
    assert MyFunctor.__mro__[2] is MappableN
    with temp_registered(
        MyFunctor.__mro__[2],
        st.builds(MyFunctor),
    ):
        assert source.draw(st.builds(target_func)) is True


A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
D = TypeVar("D")


class _FirstBase(Generic[A, B]):
    pass


class _SecondBase(Generic[C, D]):
    pass


# To be tested:


class TwoGenericBases1(_FirstBase[A, B], _SecondBase[C, D]):
    pass


class TwoGenericBases2(_FirstBase[C, D], _SecondBase[A, B]):
    pass


class OneGenericOneConrete1(_FirstBase[int, str], _SecondBase[A, B]):
    pass


class OneGenericOneConrete2(_FirstBase[A, B], _SecondBase[float, bool]):
    pass


class MixedGenerics1(_FirstBase[int, B], _SecondBase[C, bool]):
    pass


class MixedGenerics2(_FirstBase[A, str], _SecondBase[float, D]):
    pass


class AllConcrete(_FirstBase[int, str], _SecondBase[float, bool]):
    pass


_generic_test_types = (
    TwoGenericBases1,
    TwoGenericBases2,
    OneGenericOneConrete1,
    OneGenericOneConrete2,
    MixedGenerics1,
    MixedGenerics2,
    AllConcrete,
)


@pytest.mark.parametrize("type_", _generic_test_types)
def test_several_generic_bases(type_):
    with temp_registered(_FirstBase, st.builds(type_)):
        find_any(st.builds(_FirstBase))

    with temp_registered(_SecondBase, st.builds(type_)):
        find_any(st.builds(_SecondBase))


def var_generic_func1(obj: _FirstBase[A, B]):
    pass


def var_generic_func2(obj: _SecondBase[A, B]):
    pass


def concrete_generic_func1(obj: _FirstBase[int, str]):
    pass


def concrete_generic_func2(obj: _SecondBase[float, bool]):
    pass


def mixed_generic_func1(obj: _FirstBase[A, str]):
    pass


def mixed_generic_func2(obj: _SecondBase[float, D]):
    pass


@pytest.mark.parametrize("type_", _generic_test_types)
@pytest.mark.parametrize(
    "func",
    [
        var_generic_func1,
        var_generic_func2,
        concrete_generic_func1,
        concrete_generic_func2,
        mixed_generic_func1,
        mixed_generic_func2,
    ],
)
def test_several_generic_bases_functions(type_, func):
    with (
        temp_registered(_FirstBase, st.builds(type_)),
        temp_registered(_SecondBase, st.builds(type_)),
    ):
        find_any(st.builds(func))

    with temp_registered(type_, st.builds(type_)):
        find_any(st.builds(func))


def wrong_generic_func1(obj: _FirstBase[A, None]):
    pass


def wrong_generic_func2(obj: _SecondBase[None, bool]):
    pass


@pytest.mark.parametrize("func", [wrong_generic_func1, wrong_generic_func2])
def test_several_generic_bases_wrong_functions(func):
    with temp_registered(AllConcrete, st.builds(AllConcrete)):
        with pytest.raises(ResolutionFailed):
            check_can_generate_examples(st.builds(func))
