# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from functools import wraps

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument


def always_passes(*args, **kwargs):
    """Stand-in for a fixed version of an inner test.

    For example, pytest-trio would take the inner test, wrap it in an
    async-to-sync converter, and use the new func (not always_passes).
    """


@given(st.integers())
def test_can_replace_inner_test(x):
    raise AssertionError("This should be replaced")


test_can_replace_inner_test.hypothesis.inner_test = always_passes


def decorator(func):
    """An example of a common decorator pattern."""

    @wraps(func)
    def inner(*args, **kwargs):
        return func(*args, **kwargs)

    return inner


@decorator
@given(st.integers())
def test_can_replace_when_decorated(x):
    raise AssertionError("This should be replaced")


test_can_replace_when_decorated.hypothesis.inner_test = always_passes


@pytest.mark.parametrize("x", [1, 2])
@given(y=st.integers())
def test_can_replace_when_parametrized(x, y):
    raise AssertionError("This should be replaced")


test_can_replace_when_parametrized.hypothesis.inner_test = always_passes


def test_can_replace_when_original_is_invalid():
    # Invalid: @given with too many positional arguments
    @given(st.integers(), st.integers())
    def invalid_test(x):
        raise AssertionError

    invalid_test.hypothesis.inner_test = always_passes

    # Even after replacing the inner test, calling the wrapper should still
    # fail.
    with pytest.raises(InvalidArgument, match="Too many positional arguments"):
        invalid_test()


def test_inner_is_original_even_when_invalid():
    def invalid_test(x):
        raise AssertionError

    original = invalid_test

    # Invalid: @given with no arguments
    invalid_test = given()(invalid_test)

    # Verify that the test is actually invalid
    with pytest.raises(
        InvalidArgument,
        match="given must be called with at least one argument",
    ):
        invalid_test()

    assert invalid_test.hypothesis.inner_test == original


def test_invokes_inner_function_with_args_by_name():
    # Regression test for https://github.com/HypothesisWorks/hypothesis/issues/3245
    @given(st.integers())
    def test(x):
        pass

    f = test.hypothesis.inner_test
    test.hypothesis.inner_test = wraps(f)(lambda **kw: f(**kw))
    test()
