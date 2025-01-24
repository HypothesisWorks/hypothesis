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

from hypothesis import errors, given, strategies as st
from hypothesis.internal.compat import BaseExceptionGroup, ExceptionGroup
from hypothesis.strategies import DataObject


def test_discard_frozen() -> None:
    @given(st.data())
    def discard_frozen(data: DataObject) -> None:
        # Accessing .conjecture_data is internal API. Other possible ways of freezing
        # data might go through ConjectureRunner.cached_test_function_ir or
        # ConjectureRunner.test_function
        data.conjecture_data.freeze()
        # Raising Frozen doesn't actually do anything, what matters is
        # whether the data is frozen.
        raise ExceptionGroup("", [errors.Frozen()])

    discard_frozen()


def test_discard_multiple_frozen() -> None:
    @given(st.data())
    def discard_multiple_frozen(data: DataObject) -> None:
        data.conjecture_data.freeze()
        raise ExceptionGroup("", [errors.Frozen(), errors.Frozen()])

    discard_multiple_frozen()


def test_user_error_and_frozen() -> None:
    @given(st.data())
    def user_error_and_frozen(data: DataObject) -> None:
        raise ExceptionGroup("", [errors.Frozen(), TypeError()])

    with pytest.raises(ExceptionGroup) as excinfo:
        user_error_and_frozen()
    e = excinfo.value
    assert isinstance(e, ExceptionGroup)
    assert len(e.exceptions) == 2
    assert isinstance(e.exceptions[0], errors.Frozen)
    assert isinstance(e.exceptions[1], TypeError)


def test_user_error_and_stoptest() -> None:
    # if the code base had "proper" handling of exceptiongroups, the StopTest would
    # probably be handled by an except*.
    # TODO: which I suppose is an argument in favor of stripping it??
    @given(st.data())
    def user_error_and_stoptest(data: DataObject) -> None:
        raise BaseExceptionGroup(
            "", [errors.StopTest(data.conjecture_data.testcounter), TypeError()]
        )

    with pytest.raises(BaseExceptionGroup) as excinfo:
        user_error_and_stoptest()
    e = excinfo.value
    assert isinstance(e, BaseExceptionGroup)
    assert len(e.exceptions) == 2
    assert isinstance(e.exceptions[0], errors.StopTest)
    assert isinstance(e.exceptions[1], TypeError)


def test_lone_user_error() -> None:
    # we don't want to unwrap exceptiongroups, since they might contain
    # useful debugging info
    @given(st.data())
    def lone_user_error(data: DataObject) -> None:
        raise ExceptionGroup("foo", [TypeError()])

    with pytest.raises(ExceptionGroup) as excinfo:
        lone_user_error()
    e = excinfo.value
    assert isinstance(e, ExceptionGroup)
    assert len(e.exceptions) == 1
    assert isinstance(e.exceptions[0], TypeError)


def test_nested_stoptest() -> None:
    @given(st.data())
    def nested_stoptest(data: DataObject) -> None:
        raise BaseExceptionGroup(
            "",
            [
                BaseExceptionGroup(
                    "", [errors.StopTest(data.conjecture_data.testcounter)]
                )
            ],
        )

    nested_stoptest()


def test_frozen_and_stoptest() -> None:
    # frozen+stoptest => strip frozen and let engine handle StopTest
    # actually.. I don't think I've got a live repo for this either.
    @given(st.data())
    def frozen_and_stoptest(data: DataObject) -> None:
        raise BaseExceptionGroup(
            "", [errors.StopTest(data.conjecture_data.testcounter), errors.Frozen()]
        )

    frozen_and_stoptest()


def test_multiple_stoptest_1() -> None:
    # multiple stoptest, reraise the one with lowest testcounter
    @given(st.data())
    def multiple_stoptest(data: DataObject) -> None:
        c = data.conjecture_data.testcounter
        raise BaseExceptionGroup("", [errors.StopTest(c), errors.StopTest(c + 1)])

    multiple_stoptest()


def test_multiple_stoptest_2() -> None:
    # the lower value is raised, which does not match data.conjecture_data.testcounter
    # so it is not handled by the engine
    @given(st.data())
    def multiple_stoptest_2(data: DataObject) -> None:
        c = data.conjecture_data.testcounter
        raise BaseExceptionGroup("", [errors.StopTest(c), errors.StopTest(c - 1)])

    with pytest.raises(errors.StopTest):
        multiple_stoptest_2()


def test_stoptest_and_hypothesisexception() -> None:
    # current code raises the first hypothesisexception and throws away stoptest
    @given(st.data())
    def stoptest_and_hypothesisexception(data: DataObject) -> None:
        c = data.conjecture_data.testcounter
        raise BaseExceptionGroup("", [errors.StopTest(c), errors.Flaky()])

    with pytest.raises(errors.Flaky):
        stoptest_and_hypothesisexception()


def test_multiple_hypothesisexception() -> None:
    # this can happen in several ways, see nocover/test_exceptiongroup.py
    @given(st.data())
    def stoptest_and_hypothesisexception(data: DataObject) -> None:
        c = data.conjecture_data.testcounter
        raise BaseExceptionGroup("", [errors.StopTest(c), errors.Flaky()])

    with pytest.raises(errors.Flaky):
        stoptest_and_hypothesisexception()
