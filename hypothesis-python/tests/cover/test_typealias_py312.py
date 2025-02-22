# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import strategies as st

from tests.common.debug import assert_simple_property, find_any
from tests.common.utils import temp_registered


def test_resolves_simple_typealias():
    type MyInt = int
    type AliasedInt = MyInt
    type MaybeInt = int | None

    assert_simple_property(st.from_type(MyInt), lambda x: isinstance(x, int))
    assert_simple_property(st.from_type(AliasedInt), lambda x: isinstance(x, int))
    assert_simple_property(
        st.from_type(MaybeInt), lambda x: isinstance(x, int) or x is None
    )

    find_any(st.from_type(MaybeInt), lambda x: isinstance(x, int))
    find_any(st.from_type(MaybeInt), lambda x: x is None)


def test_resolves_nested():
    type Point1 = int
    type Point2 = Point1
    type Point3 = Point2

    assert_simple_property(st.from_type(Point3), lambda x: isinstance(x, int))


def test_mutually_recursive_fails():
    # example from
    # https://docs.python.org/3/library/typing.html#typing.TypeAliasType.__value__
    type A = B
    type B = A

    # I guess giving a nicer error here would be good, but detecting this in general
    # is...complicated.
    with pytest.raises(RecursionError):
        find_any(st.from_type(A))


def test_can_register_typealias():
    type A = int
    st.register_type_strategy(A, st.just("a"))
    assert_simple_property(st.from_type(A), lambda x: x == "a")


def test_prefers_manually_registered_typealias():
    # manually registering a `type A = ...` should override automatic detection
    type A = int

    assert_simple_property(st.from_type(A), lambda x: isinstance(x, int))

    with temp_registered(A, st.booleans()):
        assert_simple_property(st.from_type(A), lambda x: isinstance(x, bool))
