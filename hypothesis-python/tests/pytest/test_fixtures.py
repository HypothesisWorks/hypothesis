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

from _hypothesis_pytestplugin import item_scoped
from hypothesis import Phase, example, given, settings
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


num_func = num_item = num_param = num_ex = num_test = 0

@pytest.fixture()
def fixture_func():
    """once per example"""
    global num_func
    num_func += 1
    print("->func")
    return num_func


@pytest.fixture()
@item_scoped
def fixture_item():
    """once per test item"""
    global num_item
    num_item += 1
    print("->item")
    return num_item


@pytest.fixture()
def fixture_func_item(fixture_func, fixture_item):
    """mixed-scope transitivity"""
    return (fixture_func, fixture_item)


@pytest.fixture()
def fixture_test(fixture_test):
    """overrides conftest fixture of same name"""
    global num_test
    num_test += 1
    print("->test")
    return (fixture_test, num_test)


@pytest.fixture(params=range(1, 4))
def fixture_param(request):
    """parameterized, per-example"""
    global num_param
    print("->param")
    num_param += 1
    return (num_param, request.param)


@given(integers())
@settings(
    phases=[Phase.generate],
    max_examples=4,
)
def test_function_scoped_fixtures(fixture_func_item, fixture_test, fixture_param, fixture_test_2, _):
    global num_ex
    num_ex += 1

    # All these should be used only by this test, to avoid counter headaches
    print(f"{fixture_func_item=} {fixture_test=} {fixture_param=} {fixture_test_2=}")

    # 1. fixture_test is a tuple (num_conftest_calls, num_module_calls), and
    #    both are function-scoped so should be called per-example
    assert fixture_test == (num_ex, num_ex)
    # 2. fixture_test_2 should have picked up the module-level fixture_test, not
    #    the conftest-level one
    assert fixture_test_2 == fixture_test
    # 3. check that the parameterized fixture was also re-executed for each example
    assert fixture_param[0] == num_ex
    # 4. number of calls to _func should be the same as number of examples, while
    #    number of calls to _item should be the number of parametrized items (which
    #    is supplied by fixture_param[1] which is (1, 2, ...))
    assert fixture_func_item == (num_ex, fixture_param[1])
    #
    print("---------")


@pytest.fixture
def fixt_1(fixt_1, fixt_2):
    return f"f1_m({fixt_1}, {fixt_2})"


@pytest.fixture
def fixt_2(fixt_1, fixt_2):
    return f"f2_m({fixt_1}, {fixt_2})"


@pytest.fixture
def fixt_3(fixt_1, fixt_3):
    return f"f3_m({fixt_1}, {fixt_3})"


@pytest.mark.xfail(strict=True)
@given(integers())
#@settings(phases=[Phase.generate])  # uncomment for worse error reporting
def test_cyclic_fixture_dependency(fixt_1, fixt_2, fixt_3):
    # The below, which is the result without @given, looks arbitrary.
    # Notice how fixt_2 and fixt_3 resolve different values for fixt_1
    # (module.fixt_2 receives conftest.fixt_1, while
    #  module.fixt_3 receives module.fixt_1).
    assert fixt_1 == "f1_m(f1_c, f2_m(f1_c, f2_c(f1_c)))"
    assert fixt_2 == "f2_m(f1_c, f2_c(f1_c))"
    assert fixt_3 == "f3_m(f1_m(f1_c, f2_m(f1_c, f2_c(f1_c))), f3_c(f1_m(f1_c, f2_m(f1_c, f2_c(f1_c)))))"



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
