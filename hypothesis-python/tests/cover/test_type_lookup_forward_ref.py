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

import sys
from typing import TYPE_CHECKING, TypeVar

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import ForwardRef
from tests.common import utils
from tests.common.debug import find_any

if TYPE_CHECKING:
    from tests.common.utils import ExcInfo  # we just need any type  # noqa: F401

# Correct:

_Correct = TypeVar("_Correct", bound="CustomType")


def correct_fun(thing: _Correct) -> int:
    return thing.arg


class CustomType:
    def __init__(self, arg: int) -> None:
        self.arg = arg


@pytest.mark.skipif(sys.version_info[:2] < (3, 7), reason="typing module was broken")
@given(st.builds(correct_fun))
def test_bound_correct_forward_ref(built):
    assert isinstance(built, int)


@pytest.mark.skipif(sys.version_info[:2] >= (3, 7), reason="typing is now correct")
def test_bound_correct_forward_ref_old_versions():
    with pytest.raises(InvalidArgument):
        st.builds(correct_fun).example()


# Alises:

_Alias = TypeVar("_Alias ", bound="OurAlias")


def alias_fun(thing: _Alias) -> int:
    return thing.arg


OurAlias = CustomType


@pytest.mark.skipif(sys.version_info[:2] < (3, 7), reason="typing module was broken")
@given(st.builds(alias_fun))
def test_bound_alias_forward_ref(built):
    assert isinstance(built, int)


# Dot access:

_DotAccess = TypeVar("_DotAccess", bound="utils.ExcInfo")


def dot_access_fun(thing: _DotAccess) -> int:
    return 1


@pytest.mark.skipif(sys.version_info[:2] < (3, 7), reason="typing module was broken")
@given(st.builds(dot_access_fun))
def test_bound_dot_access_forward_ref(built):
    assert isinstance(built, int)


# Missing:

_Missing = TypeVar("_Missing", bound="MissingType")


def missing_fun(thing: _Missing) -> int:
    return 1


@pytest.mark.skipif(sys.version_info[:2] < (3, 6), reason="typing module was strange")
def test_bound_missing_forward_ref():
    with pytest.raises(InvalidArgument):
        st.builds(missing_fun).example()


# Type checking only:

_TypeChecking = TypeVar("_TypeChecking", bound="ExcInfo")


def typechecking_only_fun(thing: _TypeChecking) -> int:
    return 1


@pytest.mark.skipif(sys.version_info[:2] < (3, 7), reason="typing module was broken")
def test_bound_type_cheking_only_forward_ref():
    with utils.temp_registered(ForwardRef("ExcInfo"), st.just(1)):
        find_any(st.builds(typechecking_only_fun))


@pytest.mark.skipif(sys.version_info[:2] < (3, 7), reason="typing module was broken")
def test_bound_type_cheking_only_forward_ref_wrong_type():
    with utils.temp_registered(ForwardRef("WrongType"), st.just(1)):
        with pytest.raises(InvalidArgument):
            st.builds(typechecking_only_fun).example()
