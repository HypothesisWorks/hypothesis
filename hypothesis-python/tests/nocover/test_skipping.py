# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import unittest

import pytest

from hypothesis import given, settings
from hypothesis.core import skip_exceptions_to_reraise
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.strategies import integers

from tests.common.utils import capture_out


@pytest.mark.parametrize("skip_exception", skip_exceptions_to_reraise())
def test_no_falsifying_example_if_unittest_skip(skip_exception):
    """If a ``SkipTest`` exception is raised during a test, Hypothesis should
    not continue running the test and shrink process, nor should it print
    anything about falsifying examples."""

    class DemoTest(unittest.TestCase):
        @given(xs=integers())
        def test_to_be_skipped(self, xs):
            if xs == 0:
                raise skip_exception
            else:
                assert xs == 0

    with capture_out() as o:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(DemoTest)
        unittest.TextTestRunner().run(suite)

    assert "Falsifying example" not in o.getvalue()


def test_skip_exceptions_save_database_entries():
    """Skip exceptions should save database entries for immediate replay (issue #4484)."""
    database = InMemoryExampleDatabase()
    call_count = 0
    skip_value = None
    first_value_on_second_run = None
    is_second_run = False

    @settings(database=database, max_examples=100)
    @given(integers())
    def test_func(n):
        nonlocal call_count, skip_value, first_value_on_second_run, is_second_run
        call_count += 1
        if is_second_run and first_value_on_second_run is None:
            first_value_on_second_run = n
        # Skip on the 5th value we see in the first run
        if call_count == 5 and skip_value is None:
            skip_value = n
        if skip_value is not None and n == skip_value:
            pytest.skip(f"skipping on {n}")

    # First run should raise a skip exception and save to database
    with pytest.raises(pytest.skip.Exception):
        test_func()

    # Verify database entry was saved
    assert sum(len(v) for v in database.data.values()) == 1

    # Second run should immediately replay the skip value
    call_count = 0
    is_second_run = True

    with pytest.raises(pytest.skip.Exception):
        test_func()

    # If database entry was saved, first call should be the skip value (replayed)
    assert first_value_on_second_run == skip_value
    assert call_count == 1


def test_skip_exceptions_persist_while_skipping_then_evicted():
    """Skip entries persist while skipping, then are evicted (issue #4484)."""
    database = InMemoryExampleDatabase()
    call_count = 0
    skip_value = None
    should_skip = True
    first_value = None

    @settings(database=database, max_examples=100)
    @given(integers())
    def test_func(n):
        nonlocal call_count, skip_value, first_value
        call_count += 1
        if first_value is None:
            first_value = n
        # Skip on the 5th value we see in the first run
        if call_count == 5 and skip_value is None:
            skip_value = n
        if skip_value is not None and n == skip_value and should_skip:
            pytest.skip(f"skipping on {n}")

    # First run: skip on the 5th value
    with pytest.raises(pytest.skip.Exception):
        test_func()
    assert sum(len(v) for v in database.data.values()) == 1

    # Second and third runs: still skipping, entry persists
    for _ in range(2):
        call_count = 0
        with pytest.raises(pytest.skip.Exception):
            test_func()
        assert sum(len(v) for v in database.data.values()) == 1

    # Fourth run: no longer skip, entry should be evicted
    call_count = 0
    first_value = None
    should_skip = False
    test_func()

    # Entry was replayed (first_value should be skip_value) then evicted
    assert first_value == skip_value
    assert sum(len(v) for v in database.data.values()) == 0
