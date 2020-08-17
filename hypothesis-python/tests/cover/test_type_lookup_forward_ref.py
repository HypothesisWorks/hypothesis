from typing import TypeVar

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument

_Correct = TypeVar("_Correct", bound="CustomType")


def correct_fun(thing: _Correct) -> int:
    return thing.arg


class CustomType:
    def __init__(self, arg: int) -> None:
        self.arg = arg


@given(st.builds(correct_fun))
def test_bound_correct_forward_ref(built):
    assert isinstance(built, int)


_Alias = TypeVar("_Alias ", bound="OurAlias")


def alias_fun(thing: _Alias) -> int:
    return thing.arg


OurAlias = CustomType


@given(st.builds(alias_fun))
def test_bound_alias_forward_ref(built):
    assert isinstance(built, int)


_Missing = TypeVar("_Missing", bound="MissingType")


def missing_fun(thing: _Missing) -> int:
    return 1


def test_bound_missing_forward_ref():
    with pytest.raises(InvalidArgument):
        st.builds(missing_fun).example()
