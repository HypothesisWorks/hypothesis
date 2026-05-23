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

from hypothesis import HealthCheck, given, settings, strategies as st

DB_KEY_TESTCASE = """
from hypothesis import settings, given
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.strategies import booleans
import pytest

DB = InMemoryExampleDatabase()


@settings(database=DB)
@given(booleans())
@pytest.mark.parametrize("hi", (1, 2, 3))
@pytest.mark.xfail()
def test_dummy_for_parametrized_db_keys(hi, i):
    assert Fail  # Test *must* fail for it to end up the database anyway


def test_DB_keys_for_parametrized_test():
    assert len(DB.data) == 3
"""


def test_db_keys_for_parametrized_tests_are_unique(testdir):
    script = testdir.makepyfile(DB_KEY_TESTCASE)
    testdir.runpytest(script).assert_outcomes(xfailed=3, passed=1)


@pytest.fixture(params=["a", "b"])
def fixt(request):
    return request.param


class TestNoDifferingExecutorsHealthCheck:
    # Regression test for https://github.com/HypothesisWorks/hypothesis/issues/3733

    @given(x=st.text())
    @pytest.mark.parametrize("i", range(2))
    def test_method(self, x, i):
        pass

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(x=st.text())
    def test_method_fixture(self, x, fixt):
        pass
