# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from collections.abc import Callable
from typing import get_args, get_origin

import pytest

from hypothesis import strategies as st
from hypothesis.errors import HypothesisException
from hypothesis.strategies._internal.types import evaluate_type_alias_type

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


def test_resolves_parametrized():
    type MyList = list[int]
    assert_simple_property(
        st.from_type(MyList), lambda l: all(isinstance(x, int) for x in l)
    )


def test_mutually_recursive_fails():
    # example from
    # https://docs.python.org/3/library/typing.html#typing.TypeAliasType.__value__
    type A = B
    type B = A

    # I guess giving a nicer error here would be good, but detecting this in general
    # is...complicated.
    with pytest.raises(RecursionError):
        find_any(st.from_type(A))


def test_mutually_recursive_fails_parametrized():
    # same with parametrized types
    type A[T] = B[T]
    type B[T] = A[T]

    with pytest.raises(RecursionError):
        find_any(st.from_type(A[int]))


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


def test_resolves_parameterized_typealias():
    type A[T] = list[T]

    assert_simple_property(st.from_type(A[int]), lambda x: isinstance(x, list))
    find_any(st.from_type(A[int]), lambda x: len(x) > 0)
    assert_simple_property(
        st.from_type(A[int]), lambda x: all(isinstance(i, int) for i in x)
    )


def test_resolves_nested_parameterized_typealias():
    type Inner[T] = list[T]
    type Outer[T] = Inner[T]

    assert_simple_property(st.from_type(Outer[str]), lambda x: isinstance(x, list))
    assert_simple_property(
        st.from_type(Outer[str]), lambda x: all(isinstance(i, str) for i in x)
    )


def test_resolves_parameterized_typealias_with_literal_types():
    # Type param used in non-first position with literal types
    type MyDict[T] = dict[str, T]

    assert_simple_property(st.from_type(MyDict[int]), lambda x: isinstance(x, dict))
    assert_simple_property(
        st.from_type(MyDict[int]),
        lambda x: all(isinstance(k, str) and isinstance(v, int) for k, v in x.items()),
    )


def test_can_register_parameterized_typealias_with_unused_params():
    # Users can explicitly register strategies for such types using a resolver function
    type MyList[T1, T2] = list[T1]

    # Register a function that resolves the type alias
    def resolve_mylist(thing):
        if get_origin(thing) is MyList:
            args = get_args(thing)
            # Use the first type argument, ignore the second
            return st.lists(st.from_type(args[0]))
        return NotImplemented

    st.register_type_strategy(MyList, resolve_mylist)

    assert_simple_property(
        st.from_type(MyList[int, float]), lambda x: isinstance(x, list)
    )
    assert_simple_property(
        st.from_type(MyList[int, float]), lambda x: all(isinstance(i, int) for i in x)
    )


def test_typealias_evaluation():
    type A[T1, T2] = list[T1]
    assert evaluate_type_alias_type(A[int, float]) == list[int]

    type A[T1, T2] = list[T2]
    assert evaluate_type_alias_type(A[float, int]) == list[int]

    type A[K, V] = dict[V, K]
    assert evaluate_type_alias_type(A[str, int]) == dict[int, str]

    type A[T] = list[list[T]]
    assert evaluate_type_alias_type(A[int]) == list[list[int]]

    type Inner[T] = list[T]
    type Outer[T] = Inner[T]
    assert evaluate_type_alias_type(Outer[int]) == list[int]

    type Bare[T] = list
    assert evaluate_type_alias_type(Bare[int]) == list

    type A[T1, T2] = list[T1]
    assert evaluate_type_alias_type(A[int]) == list[int]

    # tries to reference free variable
    type A[T1, T2] = list[T2]
    with pytest.raises(ValueError):
        evaluate_type_alias_type(A[int])

    # (currently) unsupported type forms
    type A[*Ts] = tuple[*Ts]
    with pytest.raises(HypothesisException, match="Hypothesis does not yet support"):
        assert evaluate_type_alias_type(A[int, str, float]) == tuple[int, str, float]

    type A[**P] = Callable[P, int]
    with pytest.raises(HypothesisException, match="Hypothesis does not yet support"):
        assert evaluate_type_alias_type(A[[str, float]]) == Callable[[str, float], int]
