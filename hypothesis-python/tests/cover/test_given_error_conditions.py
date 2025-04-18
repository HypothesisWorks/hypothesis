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

from hypothesis import assume, given, reject, settings
from hypothesis._settings import all_settings
from hypothesis.errors import InvalidArgument, Unsatisfiable
from hypothesis.strategies import booleans, integers, nothing

from tests.common.utils import fails_with


@fails_with(Unsatisfiable)
@given(booleans())
def test_raises_unsatisfiable_if_all_false_in_finite_set(x):
    reject()


def test_does_not_raise_unsatisfiable_if_some_false_in_finite_set():
    @given(booleans())
    def test_assume_x(x):
        assume(x)

    test_assume_x()


def test_raises_unsatisfiable_if_passed_explicit_nothing():
    @given(x=nothing())
    def test_never_runs(x):
        raise Exception("Can't ever execute this")

    with pytest.raises(
        Unsatisfiable,
        match=r"Cannot generate examples from empty strategy: x=nothing\(\)",
    ):
        test_never_runs()


def test_error_if_has_no_hints():
    @given(a=...)
    def inner(a):
        pass

    with pytest.raises(InvalidArgument):
        inner()


def test_error_if_infer_all_and_has_no_hints():
    @given(...)
    def inner(a):
        pass

    with pytest.raises(InvalidArgument):
        inner()


def test_error_if_infer_is_posarg():
    @given(..., ...)
    def inner(ex1: int, ex2: int):
        pass

    with pytest.raises(InvalidArgument):
        inner()


def test_error_if_infer_is_posarg_mixed_with_kwarg():
    @given(..., ex2=...)
    def inner(ex1: int, ex2: int):
        pass

    with pytest.raises(InvalidArgument):
        inner()


def test_given_twice_is_an_error():
    @settings(deadline=None)
    @given(booleans())
    @given(integers())
    def inner(a, b):
        pass

    with pytest.raises(InvalidArgument):
        inner()


@fails_with(InvalidArgument)
def test_given_is_not_a_class_decorator():
    @given(integers())
    class test_given_is_not_a_class_decorator:
        def __init__(self, i):
            pass


def test_specific_error_for_coroutine_functions():
    @settings(database=None)
    @given(booleans())
    async def foo(x):
        pass

    with pytest.raises(
        InvalidArgument,
        match="Hypothesis doesn't know how to run async test functions",
    ):
        foo()


@pytest.mark.parametrize("setting_name", all_settings)
def test_suggests_at_settings_if_extra_kwarg_matches_setting_name(setting_name):
    val = 1

    # dynamically create functions with an extra kwarg argument which happens to
    # match a settings variable. The user probably meant @settings.
    # exec is pretty cursed here, but it does work.
    namespace = {}
    exec(
        f"""
@given(a=1, {setting_name}={val})
def foo(a):
    pass
    """,
        globals(),
        namespace,
    )

    with pytest.raises(
        InvalidArgument,
        match=rf"Did you mean @settings\({setting_name}={val}\)\?",
    ):
        namespace["foo"]()
