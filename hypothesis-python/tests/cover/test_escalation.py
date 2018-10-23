# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import pytest

import hypothesis.strategies as st
import hypothesis.internal.escalation as esc
from hypothesis import given


def test_does_not_escalate_errors_in_non_hypothesis_file():
    try:
        assert False
    except AssertionError:
        esc.escalate_hypothesis_internal_error()


def test_does_escalate_errors_in_hypothesis_file(monkeypatch):
    monkeypatch.setattr(esc, 'is_hypothesis_file', lambda x: True)

    with pytest.raises(AssertionError):
        try:
            assert False
        except AssertionError:
            esc.escalate_hypothesis_internal_error()


def test_does_not_escalate_errors_in_hypothesis_file_if_disabled(monkeypatch):
    monkeypatch.setattr(esc, 'is_hypothesis_file', lambda x: True)
    monkeypatch.setattr(esc, 'PREVENT_ESCALATION', True)

    try:
        assert False
    except AssertionError:
        esc.escalate_hypothesis_internal_error()


def test_immediately_escalates_errors_in_generation():
    count = [0]

    def explode(s):
        count[0] += 1
        raise ValueError()

    @given(st.integers().map(explode))
    def test(i):
        pass

    with pytest.raises(ValueError):
        test()

    assert count == [1]
