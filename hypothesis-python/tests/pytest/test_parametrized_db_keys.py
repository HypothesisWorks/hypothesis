# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

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
    assert len(DB.data) == 6
"""


def test_db_keys_for_parametrized_tests_are_unique(testdir):
    script = testdir.makepyfile(DB_KEY_TESTCASE)
    testdir.runpytest(script).assert_outcomes(xfailed=3, passed=1)
