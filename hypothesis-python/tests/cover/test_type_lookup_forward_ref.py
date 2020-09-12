# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

"""
We need these test to make sure ``TypeVar('X', bound='MyType')`` works correctly.

There was a problem previously that ``bound='MyType'`` was resolved as ``ForwardRef('MyType')``
which is not a real type. And ``hypothesis`` was not able to generate any meaningful values out of it.

Right here we test different possible outcomes for different Python versions (excluding ``3.5``):
- Regular case, when ``'MyType'`` can be imported
- Alias case, when we use type aliases for ``'MyType'``
- ``if TYPE_CHECKING:`` case, when ``'MyType'`` only exists during type checking and is not importable at all
- Dot access case, like ``'module.MyType'``
- Missing case, when there's no ``'MyType'`` at all

We also separate how ``3.6`` works, because it has its limitations.
Basically, ``TypeVar`` has no information about the module it was defined at.
"""

import sys
from typing import TYPE_CHECKING, TypeVar

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import ResolutionFailed
from hypothesis.internal.compat import ForwardRef
from tests.common import utils

if TYPE_CHECKING:
    from tests.common.utils import ExcInfo  # we just need any type  # noqa: F401

skip_before_python37 = pytest.mark.skipif(
    sys.version_info[:2] < (3, 7), reason="typing module was broken"
)

# Correct:

_Correct = TypeVar("_Correct", bound="CustomType")


def correct_fun(thing: _Correct) -> int:
    return thing.arg


class CustomType:
    def __init__(self, arg: int) -> None:
        self.arg = arg


@skip_before_python37
@given(st.builds(correct_fun))
def test_bound_correct_forward_ref(built):
    """Correct resolution of existing type in ``python3.7+`` codebase."""
    assert isinstance(built, int)


@pytest.mark.skipif(
    sys.version_info[:2] != (3, 6), reason="typing in python3.6 is partially working"
)
def test_bound_correct_forward_ref_python36():
    """
    Very special case for ``python3.6`` where we have this feature partially suported.

    Due to ``TypeVar`` module definition bug.
    """
    with pytest.raises(ResolutionFailed):
        st.builds(correct_fun).example()


# Alises:

_Alias = TypeVar("_Alias ", bound="OurAlias")


def alias_fun(thing: _Alias) -> int:
    return thing.arg


OurAlias = CustomType


@skip_before_python37
@given(st.builds(alias_fun))
def test_bound_alias_forward_ref(built):
    """Correct resolution of type aliases in ``python3.7+``."""
    assert isinstance(built, int)


# Dot access:

_CorrectDotAccess = TypeVar("_CorrectDotAccess", bound="utils.ExcInfo")
_WrongDotAccess = TypeVar("_WrongDotAccess", bound="wrong.ExcInfo")
_MissingDotAccess = TypeVar("_MissingDotAccess", bound="utils.MissingType")


def correct_dot_access_fun(thing: _CorrectDotAccess) -> int:
    return 1


def wrong_dot_access_fun(thing: _WrongDotAccess) -> int:
    return 1


def missing_dot_access_fun(thing: _MissingDotAccess) -> int:
    return 1


@skip_before_python37
@given(st.builds(correct_dot_access_fun))
def test_bound_correct_dot_access_forward_ref(built):
    """Correct resolution of dot access types in ``python3.7+``."""
    assert isinstance(built, int)


@skip_before_python37
@pytest.mark.parametrize("function", [wrong_dot_access_fun, missing_dot_access_fun])
def test_bound_missing_dot_access_forward_ref(function):
    """Resolution of missing type in dot access in ``python3.7+``."""
    with pytest.raises(ResolutionFailed):
        st.builds(function).example()


# Missing:

_Missing = TypeVar("_Missing", bound="MissingType")


def missing_fun(thing: _Missing) -> int:
    return 1


@pytest.mark.skipif(sys.version_info[:2] < (3, 6), reason="typing module was strange")
def test_bound_missing_forward_ref():
    """We should raise proper errors on missing types."""
    with pytest.raises(ResolutionFailed):
        st.builds(missing_fun).example()


# Type checking only:

_TypeChecking = TypeVar("_TypeChecking", bound="ExcInfo")


def typechecking_only_fun(thing: _TypeChecking) -> int:
    return 1


@skip_before_python37
def test_bound_type_cheking_only_forward_ref():
    """We should fallback to registering explicit ``ForwardRef`` when we have to."""
    with utils.temp_registered(ForwardRef("ExcInfo"), st.just(1)):
        st.builds(typechecking_only_fun).example()


@skip_before_python37
def test_bound_type_cheking_only_forward_ref_wrong_type():
    """We should check ``ForwardRef`` parameter name correctly."""
    with utils.temp_registered(ForwardRef("WrongType"), st.just(1)):
        with pytest.raises(ResolutionFailed):
            st.builds(typechecking_only_fun).example()
