# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from inspect import signature
from typing import Optional, get_type_hints

from hypothesis import given, strategies as st

from tests.common.debug import find_any


def use_this_signature(self, a: int, b: Optional[list] = None, *, x: float, y: str):
    pass


class Model:
    # Emulates the implementation of Pydantic models.  See e.g.
    # https://github.com/timothycrosley/hypothesis-auto/issues/10
    __annotations__ = get_type_hints(use_this_signature)
    __signature__ = signature(use_this_signature)

    def __init__(self, **kwargs):
        # Check that we're being called with the expected arguments
        assert set(kwargs) == {"a", "x", "y"}
        assert isinstance(kwargs["a"], int)
        assert isinstance(kwargs["x"], float)
        assert isinstance(kwargs["y"], str)


@given(st.builds(Model))
def test_builds_uses_signature_attribute(val):
    assert isinstance(val, Model)


class ModelForFromType(Model):
    def __init__(self, **kwargs):
        assert set(kwargs) == {"a", "b", "x", "y"}
        self.b = kwargs["b"]
        assert self.b is None or isinstance(self.b, list)


@given(st.from_type(ModelForFromType))
def test_from_type_uses_signature_attribute(val):
    assert isinstance(val, ModelForFromType)


def test_from_type_can_be_default_or_annotation():
    find_any(st.from_type(ModelForFromType), lambda m: m.b is None)
    find_any(st.from_type(ModelForFromType), lambda m: isinstance(m.b, list))


def use_annotations(
    self, test_a: int, test_b: Optional[str] = None, *, test_x: float, test_y: str
):
    pass


def use_signature(
    self, testA: int, testB: Optional[str] = None, *, testX: float, testY: list[str]
):
    pass


class ModelWithAlias:
    __annotations__ = get_type_hints(use_annotations)
    __signature__ = signature(use_signature)

    def __init__(self, **kwargs):
        # Check that we're being called with the expected arguments
        assert set(kwargs) == {"testA", "testX", "testY"}
        assert isinstance(kwargs["testA"], int)
        assert isinstance(kwargs["testX"], float)
        assert isinstance(kwargs["testY"], list)
        assert all(isinstance(elem, str) for elem in kwargs["testY"])


@given(st.builds(ModelWithAlias))
def test_build_using_different_signature_and_annotations(val):
    assert isinstance(val, ModelWithAlias)


def use_bad_signature(self, testA: 1, *, testX: float):
    pass


class ModelWithBadAliasSignature:
    __annotations__ = get_type_hints(use_annotations)
    __signature__ = signature(use_bad_signature)

    def __init__(self, **kwargs):
        assert set(kwargs) == {"testX"}
        assert isinstance(kwargs["testX"], float)


@given(st.builds(ModelWithBadAliasSignature))
def test_build_with_non_types_in_signature(val):
    assert isinstance(val, ModelWithBadAliasSignature)


class UnconventionalSignature:
    def __init__(x: int = 0, self: bool = True):  # noqa
        assert not isinstance(x, int)
        x.self = self


def test_build_in_from_type_with_self_named_something_else():
    find_any(st.from_type(UnconventionalSignature), lambda x: x.self is True)
    find_any(st.from_type(UnconventionalSignature), lambda x: x.self is False)
