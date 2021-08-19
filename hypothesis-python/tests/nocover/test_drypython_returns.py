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

from typing import Generic, TypeVar

from hypothesis import given, strategies as st

from tests.common.utils import temp_registered

# Primitives:
# ===========

_InstanceType = TypeVar("_InstanceType", covariant=True)
_TypeArgType1 = TypeVar("_TypeArgType1", covariant=True)
_FirstType = TypeVar("_FirstType")
_LawType = TypeVar("_LawType")


class KindN(
    Generic[_InstanceType, _TypeArgType1],
):
    pass


class Lawful(Generic[_LawType]):
    """This type defines law-related operations."""


class MappableN(
    Generic[_FirstType],
    # NOTE: Here's the problematic part for issue-3060:
    Lawful["MappableN[_FirstType]"],
):
    """Behaves like a functor."""


# End definition:
# ===============

_ValueType = TypeVar("_ValueType")


class MyFunctor(
    KindN["MyFunctor", _ValueType],
    MappableN[_ValueType],
):
    def __init__(self, inner_value: _ValueType) -> None:
        self.inner_value = inner_value


# Testing part:
# =============


def target_func(
    mappable: "MappableN[_FirstType]",
) -> bool:
    return isinstance(mappable, MappableN)


@given(st.data())
def test_my_mappable(source: st.DataObject) -> None:
    """
    Checks that complex types with multiple inheritance levels and strings are fine.

    Regression to https://github.com/HypothesisWorks/hypothesis/issues/3060
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
