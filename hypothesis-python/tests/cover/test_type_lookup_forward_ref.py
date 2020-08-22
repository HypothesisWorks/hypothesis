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


def test_bound_missing_forward_ref():
    with pytest.raises(InvalidArgument):
        st.builds(missing_fun).example()


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
