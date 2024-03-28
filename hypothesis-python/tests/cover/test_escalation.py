# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import os

import pytest

import hypothesis
from hypothesis import errors
from hypothesis.internal import escalation as esc
from hypothesis.internal.compat import BaseExceptionGroup


def test_does_not_escalate_errors_in_non_hypothesis_file():
    try:
        raise AssertionError
    except AssertionError:
        esc.escalate_hypothesis_internal_error()


def test_does_escalate_errors_in_hypothesis_file(monkeypatch):
    monkeypatch.setattr(esc, "is_hypothesis_file", lambda x: True)

    with pytest.raises(AssertionError):
        try:
            raise AssertionError
        except AssertionError:
            esc.escalate_hypothesis_internal_error()


def test_does_not_escalate_errors_in_hypothesis_file_if_disabled(monkeypatch):
    monkeypatch.setattr(esc, "is_hypothesis_file", lambda x: True)
    monkeypatch.setattr(esc, "PREVENT_ESCALATION", True)

    try:
        raise AssertionError
    except AssertionError:
        esc.escalate_hypothesis_internal_error()


def test_is_hypothesis_file_not_confused_by_prefix(monkeypatch):
    # Errors in third-party extensions such as `hypothesis-trio` or
    # `hypothesis-jsonschema` used to be incorrectly considered to be
    # Hypothesis internal errors, which could result in confusing error
    # messages. This test makes sure that files like:
    # `[...]/python3.7/site-packages/hypothesis_something/[...]`
    # are not considered as hypothesis files.
    root = os.path.dirname(hypothesis.__file__)
    assert esc.is_hypothesis_file(hypothesis.__file__)
    assert esc.is_hypothesis_file(esc.__file__)

    assert not esc.is_hypothesis_file(pytest.__file__)
    assert not esc.is_hypothesis_file(root + "-suffix")
    assert not esc.is_hypothesis_file(root + "-suffix/something.py")


@pytest.mark.parametrize("fname", ["", "<ipython-input-18-f7c304bea5eb>"])
def test_is_hypothesis_file_does_not_error_on_invalid_paths_issue_2319(fname):
    assert not esc.is_hypothesis_file(fname)


def test_multiplefailures_deprecation():
    with pytest.warns(errors.HypothesisDeprecationWarning):
        exc = errors.MultipleFailures
    assert exc is BaseExceptionGroup


def test_errors_attribute_error():
    with pytest.raises(AttributeError):
        errors.ThisIsNotARealAttributeDontCreateSomethingWithThisName


def test_handles_null_traceback():
    esc.InterestingOrigin.from_exception(Exception())


def test_handles_context():
    e = ValueError()
    e.__context__ = KeyError()
    origin = esc.InterestingOrigin.from_exception(e)
    assert "ValueError at " in str(origin)
    assert "  context: " in str(origin)
    assert "KeyError at " in str(origin)


def test_handles_groups():
    origin = esc.InterestingOrigin.from_exception(
        BaseExceptionGroup("message", [ValueError("msg2")])
    )
    assert "ExceptionGroup at " in str(origin)
    assert "child exception" in str(origin)
    assert "ValueError at " in str(origin)


def test_conflates_repeat_exceptions_for_equality():
    errors = [ValueError(""), ValueError("")]

    o1 = esc.InterestingOrigin.from_exception(BaseExceptionGroup("message", errors))
    o2 = esc.InterestingOrigin.from_exception(BaseExceptionGroup("message", errors[:1]))

    assert o1.group_elems != o2.group_elems
    assert o1 == o2
    assert hash(o1) == hash(o2)
