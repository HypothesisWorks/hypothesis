# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import Mock, create_autospec

import pytest

from hypothesis import example, given
from hypothesis.strategies import integers

from tests.common.utils import fails

pytest_plugins = "pytester"


@pytest.fixture(scope="session")
def infinity():
    return float("inf")


@pytest.fixture(scope="module")
def mock_fixture():
    return Mock()


@pytest.fixture(scope="module")
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
    raise AssertionError


@given(integers())
def test_can_inject_autospecced_mock_via_fixture(spec_fixture, xs):
    spec_fixture.bar.return_value = float("inf")
    assert xs <= spec_fixture.bar()


TESTSUITE = """
import pytest
from hypothesis import given, strategies as st

@pytest.fixture(scope="function", autouse=True)
def autofix(request):
    pass

@given(x=st.integers())
def test_requests_function_scoped_fixture(capsys, x):
    pass

@pytest.mark.parametrize("percent", ["%", "%s"])
@given(x=st.integers())
def test_requests_function_scoped_fixture_percent_parametrized(capsys, x, percent):
    # See https://github.com/HypothesisWorks/hypothesis/issues/2469
    pass

class TestClass:
    @given(x=st.integers())
    def test_requests_method_scoped_fixture(capsys, x):
        pass

@given(x=st.integers())
def test_autouse_function_scoped_fixture(x):
    pass
"""


def test_given_plus_function_scoped_non_autouse_fixtures_are_deprecated(testdir):
    script = testdir.makepyfile(TESTSUITE)
    testdir.runpytest(script).assert_outcomes(passed=1, failed=4)


CONFTEST_SUPPRESS = """
from hypothesis import HealthCheck, settings

settings.register_profile(
    "suppress",
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
"""


def test_suppress_fixture_health_check_via_profile(testdir):
    script = testdir.makepyfile(TESTSUITE)
    testdir.makeconftest(CONFTEST_SUPPRESS)

    testdir.runpytest(script).assert_outcomes(passed=1, failed=4)
    testdir.runpytest(script, "--hypothesis-profile=suppress").assert_outcomes(passed=5)


TESTSCRIPT_SUPPRESS_FIXTURE = """
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

@given(x=st.integers())
def test_fails_health_check(capsys, x):
    pass

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(x=st.integers())
def test_suppresses_health_check(capsys, x):
    pass

@given(x=st.integers())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_suppresses_health_check_2(capsys, x):
    pass
"""


def test_suppress_health_check_function_scoped_fixture(testdir):
    script = testdir.makepyfile(TESTSCRIPT_SUPPRESS_FIXTURE)
    testdir.runpytest(script).assert_outcomes(passed=2, failed=1)


TESTSCRIPT_OVERRIDE_FIXTURE = """
import pytest
from hypothesis import given, strategies as st

@pytest.fixture(scope="function", name="event_loop")
def event_loop_1():
    return

@pytest.fixture(scope="module", name="event_loop")
def event_loop_2():
    return

@given(x=st.integers())
def test_override_fixture(event_loop, x):
    pass
"""


def test_given_plus_overridden_fixture(testdir):
    script = testdir.makepyfile(TESTSCRIPT_OVERRIDE_FIXTURE)
    testdir.runpytest(script, "-Werror").assert_outcomes(passed=1, failed=0)


TESTSCRIPT_FIXTURE_THEN_GIVEN = """
import pytest
from hypothesis import given, strategies as st

@given(x=st.integers())
@pytest.fixture()
def test(x):
    pass
"""


def test_given_fails_if_already_decorated_with_fixture(testdir):
    script = testdir.makepyfile(TESTSCRIPT_FIXTURE_THEN_GIVEN)
    testdir.runpytest(script).assert_outcomes(failed=1)


TESTSCRIPT_GIVEN_THEN_FIXTURE = """
import pytest
from hypothesis import given, strategies as st

@pytest.fixture()
@given(x=st.integers())
def test(x):
    pass
"""


def test_fixture_errors_if_already_decorated_with_given(testdir):
    script = testdir.makepyfile(TESTSCRIPT_GIVEN_THEN_FIXTURE)
    if int(pytest.__version__.split(".")[0]) > 5:
        testdir.runpytest(script).assert_outcomes(errors=1)
    else:
        testdir.runpytest(script).assert_outcomes(error=1)
