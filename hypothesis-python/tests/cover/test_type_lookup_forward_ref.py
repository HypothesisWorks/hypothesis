# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""
We need these test to make sure ``TypeVar('X', bound='MyType')`` works correctly.

There was a problem previously that ``bound='MyType'`` was resolved as ``ForwardRef('MyType')``
which is not a real type. And ``hypothesis`` was not able to generate any meaningful values out of it.

Right here we test different possible outcomes for different Python versions:
- Regular case, when ``'MyType'`` can be imported
- Alias case, when we use type aliases for ``'MyType'``
- ``if TYPE_CHECKING:`` case, when ``'MyType'`` only exists during type checking and is not importable at all
- Dot access case, like ``'module.MyType'``
- Missing case, when there's no ``'MyType'`` at all
"""

from typing import TYPE_CHECKING, ForwardRef, TypeVar

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import ResolutionFailed

from tests.common import utils
from tests.common.debug import check_can_generate_examples

if TYPE_CHECKING:
    from tests.common.utils import ExcInfo  # we just need any type

# Correct:

_Correct = TypeVar("_Correct", bound="CustomType")


def correct_fun(thing: _Correct) -> int:
    return thing.arg


class CustomType:
    def __init__(self, arg: int) -> None:
        self.arg = arg


@given(st.builds(correct_fun))
def test_bound_correct_forward_ref(built):
    """Correct resolution of existing type codebase."""
    assert isinstance(built, int)


# Aliases:

_Alias = TypeVar("_Alias ", bound="OurAlias")


def alias_fun(thing: _Alias) -> int:
    return thing.arg


OurAlias = CustomType


@given(st.builds(alias_fun))
def test_bound_alias_forward_ref(built):
    """Correct resolution of type aliases."""
    assert isinstance(built, int)


# Dot access:

_CorrectDotAccess = TypeVar("_CorrectDotAccess", bound="utils.ExcInfo")
_WrongDotAccess = TypeVar("_WrongDotAccess", bound="wrong.ExcInfo")  # noqa
_MissingDotAccess = TypeVar("_MissingDotAccess", bound="utils.MissingType")


def correct_dot_access_fun(thing: _CorrectDotAccess) -> int:
    return 1


def wrong_dot_access_fun(thing: _WrongDotAccess) -> int:
    return 1


def missing_dot_access_fun(thing: _MissingDotAccess) -> int:
    return 1


@given(st.builds(correct_dot_access_fun))
def test_bound_correct_dot_access_forward_ref(built):
    """Correct resolution of dot access types."""
    assert isinstance(built, int)


@pytest.mark.parametrize("function", [wrong_dot_access_fun, missing_dot_access_fun])
def test_bound_missing_dot_access_forward_ref(function):
    """Resolution of missing type in dot access."""
    with pytest.raises(ResolutionFailed):
        check_can_generate_examples(st.builds(function))


# Missing:

_Missing = TypeVar("_Missing", bound="MissingType")  # noqa


def missing_fun(thing: _Missing) -> int:
    return 1


def test_bound_missing_forward_ref():
    """We should raise proper errors on missing types."""
    with pytest.raises(ResolutionFailed):
        check_can_generate_examples(st.builds(missing_fun))


# Type checking only:

_TypeChecking = TypeVar("_TypeChecking", bound="ExcInfo")


def typechecking_only_fun(thing: _TypeChecking) -> int:
    return 1


def test_bound_type_cheking_only_forward_ref():
    """We should fallback to registering explicit ``ForwardRef`` when we have to."""
    with utils.temp_registered(ForwardRef("ExcInfo"), st.just(1)):
        check_can_generate_examples(st.builds(typechecking_only_fun))


def test_bound_type_checking_only_forward_ref_wrong_type():
    """We should check ``ForwardRef`` parameter name correctly."""
    with utils.temp_registered(ForwardRef("WrongType"), st.just(1)):
        with pytest.raises(ResolutionFailed):
            check_can_generate_examples(st.builds(typechecking_only_fun))
