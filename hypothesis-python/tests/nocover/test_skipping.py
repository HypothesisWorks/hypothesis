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

from hypothesis import given
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
