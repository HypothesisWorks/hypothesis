# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Checks that @given, @mock.patch, and pytest fixtures work as expected."""


import math
from unittest import mock

try:
    from pytest import Config
except ImportError:  # pytest<7.0.0
    from _pytest.config import Config

from hypothesis import given, strategies as st


@given(thing=st.text())
@mock.patch("math.atan")
def test_can_mock_inside_given_without_fixture(atan, thing):
    assert isinstance(atan, mock.MagicMock)
    assert isinstance(math.atan, mock.MagicMock)


@mock.patch("math.atan")
@given(thing=st.text())
def test_can_mock_outside_given_with_fixture(atan, pytestconfig, thing):
    assert isinstance(atan, mock.MagicMock)
    assert isinstance(math.atan, mock.MagicMock)
    assert isinstance(pytestconfig, Config)


@given(thing=st.text())
def test_can_mock_within_test_with_fixture(pytestconfig, thing):
    assert isinstance(pytestconfig, Config)
    assert not isinstance(math.atan, mock.MagicMock)
    with mock.patch("math.atan") as atan:
        assert isinstance(atan, mock.MagicMock)
        assert isinstance(math.atan, mock.MagicMock)
    assert not isinstance(math.atan, mock.MagicMock)
