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

from hypothesis import Phase, given, settings
from hypothesis.core import skip_exceptions_to_reraise
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


def test_skip_exceptions_are_saved_to_database():
    """Skip exceptions should be saved to the database so they can be replayed
    immediately on subsequent runs (issue #4484)."""

    from hypothesis.database import InMemoryExampleDatabase

    db = InMemoryExampleDatabase()
    skip_value = 42

    # First run: with Phase.reuse disabled, find and skip at the target value
    @settings(
        database=db,
        max_examples=200,
        phases=[Phase.explicit, Phase.generate, Phase.target, Phase.shrink],
    )
    @given(x=integers(min_value=0, max_value=100))
    def test_skip_generate(x):
        if x == skip_value:
            raise unittest.SkipTest(f"Skipping at x={skip_value}")

    # Run the test until it skips
    with pytest.raises(unittest.SkipTest):
        test_skip_generate()

    # Second run: with only Phase.reuse enabled, it should still skip because
    # the skip exception was saved to the database
    @settings(database=db, phases=[Phase.reuse])
    @given(x=integers(min_value=0, max_value=100))
    def test_skip_reuse(x):
        if x == skip_value:
            raise unittest.SkipTest(f"Skipping at x={skip_value}")

    # This should also skip because the database entry is replayed
    with pytest.raises(unittest.SkipTest):
        test_skip_reuse()
