# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass

import pytest

from hypothesis import Verbosity, assume, given, reject, reporting, settings
from hypothesis.control import (
    BuildContext,
    _current_build_context,
    _event_to_string,
    cleanup,
    current_build_context,
    currently_in_test_context,
    event,
    note,
)
from hypothesis.errors import (
    HypothesisDeprecationWarning,
    InvalidArgument,
    UnsatisfiedAssumption,
)
from hypothesis.internal.compat import ExceptionGroup
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.stateful import RuleBasedStateMachine, rule
from hypothesis.strategies import integers

from tests.common.utils import capture_out


def bc():
    return BuildContext(ConjectureData.for_choices([]))


def test_cannot_cleanup_with_no_context():
    with pytest.raises(InvalidArgument):
        cleanup(lambda: None)
    assert _current_build_context.value is None


def test_cannot_event_with_no_context():
    with pytest.raises(InvalidArgument):
        event("hi")
    assert _current_build_context.value is None


def test_cleanup_executes_on_leaving_build_context():
    data = []
    with bc():
        cleanup(lambda: data.append(1))
        assert not data
    assert data == [1]
    assert _current_build_context.value is None


def test_can_nest_build_context():
    data = []
    with bc():
        cleanup(lambda: data.append(1))
        with bc():
            cleanup(lambda: data.append(2))
            assert not data
        assert data == [2]
    assert data == [2, 1]
    assert _current_build_context.value is None


def test_does_not_suppress_exceptions():
    with pytest.raises(AssertionError):
        with bc():
            raise AssertionError
    assert _current_build_context.value is None


def test_suppresses_exceptions_in_teardown():
    with pytest.raises(ValueError) as exc_info:
        with bc():

            def foo():
                raise ValueError

            cleanup(foo)
            raise AssertionError

    assert isinstance(exc_info.value, ValueError)
    assert isinstance(exc_info.value.__cause__, AssertionError)


def test_runs_multiple_cleanup_with_teardown():
    with pytest.raises(ExceptionGroup) as exc_info:
        with bc():

            def foo():
                raise ValueError

            def bar():
                raise TypeError

            cleanup(foo)
            cleanup(bar)
            raise AssertionError

    assert isinstance(exc_info.value, ExceptionGroup)
    assert isinstance(exc_info.value.__cause__, AssertionError)
    assert {type(e) for e in exc_info.value.exceptions} == {ValueError, TypeError}
    assert _current_build_context.value is None


def test_raises_error_if_cleanup_fails_but_block_does_not():
    with pytest.raises(ValueError):
        with bc():

            def foo():
                raise ValueError

            cleanup(foo)
    assert _current_build_context.value is None


def test_raises_if_note_out_of_context():
    with pytest.raises(InvalidArgument):
        note("Hi")


def test_deprecation_warning_if_assume_out_of_context():
    with pytest.warns(
        HypothesisDeprecationWarning,
        match="Using `assume` outside a property-based test is deprecated",
    ):
        assume(True)


def test_deprecation_warning_if_reject_out_of_context():
    with pytest.warns(
        HypothesisDeprecationWarning,
        match="Using `reject` outside a property-based test is deprecated",
    ):
        with pytest.raises(UnsatisfiedAssumption):
            reject()


def test_raises_if_current_build_context_out_of_context():
    with pytest.raises(InvalidArgument):
        current_build_context()


def test_current_build_context_is_current():
    with bc() as a:
        assert current_build_context() is a


def test_prints_all_notes_in_verbose_mode():
    # slightly roundabout because @example messes with verbosity - see #1521
    messages = set()

    @settings(verbosity=Verbosity.debug, database=None)
    @given(integers(1, 10))
    def test(x):
        msg = f"x -> {x}"
        note(msg)
        messages.add(msg)
        assert x < 5

    with capture_out() as out:
        with reporting.with_reporter(reporting.default):
            with pytest.raises(AssertionError):
                test()
    v = out.getvalue()
    for x in sorted(messages):
        assert x in v


@dataclass
class CanBePrettyPrinted:
    n: int


def test_note_pretty_prints():
    reports = []

    @given(integers(1, 10))
    def test(n):
        with reporting.with_reporter(reports.append):
            note(CanBePrettyPrinted(n))
        assert n != 5

    with pytest.raises(AssertionError):
        test()

    assert reports == ["CanBePrettyPrinted(n=5)"]


def test_not_currently_in_hypothesis():
    assert currently_in_test_context() is False


@given(integers())
def test_currently_in_hypothesis(_):
    assert currently_in_test_context() is True


class ContextMachine(RuleBasedStateMachine):
    @rule()
    def step(self):
        assert currently_in_test_context() is True


test_currently_in_stateful_test = ContextMachine.TestCase


def test_can_convert_non_weakref_types_to_event_strings():
    _event_to_string(())
