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

import pytest

from hypothesis import example, given
from hypothesis.strategies import integers
from tests.common.utils import fails

try:
    from unittest.mock import Mock, create_autospec
except ImportError:
    from mock import Mock, create_autospec


@pytest.fixture
def infinity():
    return float("inf")


@pytest.fixture
def mock_fixture():
    return Mock()


@pytest.fixture
def spec_fixture():
    class Foo:
        def __init__(self):
            pass

        def bar(self):
            return "baz"

    return create_autospec(Foo)


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
def test_can_inject_mock_via_fixture(mock_fixture, xs):
    """A negative test is better for this one - this condition uncovers a bug
    whereby the mock fixture is executed instead of the test body and always
    succeeds. If this test fails, then we know we've run the test body instead
    of the mock.
    """
    assert False


@given(integers())
def test_can_inject_autospecced_mock_via_fixture(spec_fixture, xs):
    spec_fixture.bar.return_value = float("inf")
    assert xs <= spec_fixture.bar()
