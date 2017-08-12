# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

from mock import Mock, MagicMock, NonCallableMock, NonCallableMagicMock
from hypothesis import given, example
from tests.common.utils import fails
from hypothesis.strategies import integers


@pytest.fixture
def infinity():
    return float('inf')


@pytest.fixture
def m_fixture():
    return Mock()


@pytest.fixture
def mm_fixture():
    return MagicMock()


@pytest.fixture
def ncmm_fixture():
    return NonCallableMagicMock()


@pytest.fixture
def ncm_fixture():
    return NonCallableMock()


@given(integers())
def test_can_mix_fixture_and_positional_strategy(infinity, xs):
    # Hypothesis fills arguments from the right, so if @given() uses
    # positional arguments then any strategies need to be on the right.
    assert xs <= infinity


@given(xs=integers())
def test_can_mix_fixture_and_keyword_strategy(xs, infinity):
    assert xs <= infinity


@example(xs=0)
@given(xs=integers())
def test_can_mix_fixture_example_and_keyword_strategy(xs, infinity):
    assert xs <= infinity


@fails
@given(integers())
def test_can_inject_mock_via_fixture(m_fixture, x):
    assert False


@fails
@given(integers())
def test_can_inject_magicmock_via_fixture(mm_fixture, x):
    assert False


@fails
@given(integers())
def test_can_inject_nc_mock_via_fixture(ncm_fixture, x):
    assert False


@fails
@given(integers())
def test_can_inject_nc_magicmock_via_fixture(ncmm_fixture, x):
    assert False
