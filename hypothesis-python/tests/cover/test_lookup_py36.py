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

import typing

import pytest

from hypothesis import given, strategies as st
from hypothesis.internal.compat import PYPY


class TreeForwardRefs(typing.NamedTuple):
    val: int
    l: typing.Optional["TreeForwardRefs"]
    r: typing.Optional["TreeForwardRefs"]


@pytest.mark.skipif(PYPY, reason="pypy36 does not resolve the forward refs")
@given(st.builds(TreeForwardRefs))
def test_resolves_forward_references_outside_annotations(t):
    assert isinstance(t, TreeForwardRefs)


_ValueType = typing.TypeVar("_ValueType")


class Wrapper(typing.Generic[_ValueType]):
    _inner_value: _ValueType

    def __init__(self, inner_value: _ValueType) -> None:
        self._inner_value = inner_value


@given(st.builds(Wrapper))
def test_issue_2603_regression(built):
    """It was impossible to build annotated classes with constructors."""
    assert isinstance(built, Wrapper)


class AnnotatedConstructor(typing.Generic[_ValueType]):
    value: _ValueType  # the same name we have in `__init__`

    def __init__(self, value: int) -> None:
        """By this example we show, that ``int`` is more important than ``_ValueType``."""
        assert isinstance(value, int)


@given(st.data())
def test_constructor_is_more_important(data):
    """Constructor types should take presence over all other annotations."""
    data.draw(st.builds(AnnotatedConstructor))
