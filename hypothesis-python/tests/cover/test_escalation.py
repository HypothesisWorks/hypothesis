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

import os

import pytest

import hypothesis
from hypothesis.internal import escalation as esc


def test_does_not_escalate_errors_in_non_hypothesis_file():
    try:
        assert False
    except AssertionError:
        esc.escalate_hypothesis_internal_error()


def test_does_escalate_errors_in_hypothesis_file(monkeypatch):
    monkeypatch.setattr(esc, "is_hypothesis_file", lambda x: True)

    with pytest.raises(AssertionError):
        try:
            assert False
        except AssertionError:
            esc.escalate_hypothesis_internal_error()


def test_does_not_escalate_errors_in_hypothesis_file_if_disabled(monkeypatch):
    monkeypatch.setattr(esc, "is_hypothesis_file", lambda x: True)
    monkeypatch.setattr(esc, "PREVENT_ESCALATION", True)

    try:
        assert False
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
