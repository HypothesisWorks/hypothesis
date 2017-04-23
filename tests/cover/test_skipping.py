# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

import unittest

import nose
import pytest
import unittest2

from hypothesis import given
from hypothesis.strategies import integers
from tests.common.utils import capture_out


@pytest.mark.parametrize('unittest_mod, skip_exception', [
    (unittest, unittest.SkipTest()),
    (unittest2, unittest2.SkipTest()),
    (unittest, nose.SkipTest()),
])
def test_no_falsifying_example_if_unittest_skip(unittest_mod, skip_exception):
    """If a ``SkipTest`` exception is raised during a test, Hypothesis
    should not continue running the test and shrink process, nor should
    it print anything about falsifying examples.

    """
    class DemoTest(unittest_mod.TestCase):

        @given(xs=integers())
        def test_to_be_skipped(self, xs):
            if xs == 0:
                raise skip_exception
            else:
                assert xs == 0

    with capture_out() as o:
        suite = unittest_mod.defaultTestLoader.loadTestsFromTestCase(DemoTest)
        unittest_mod.TextTestRunner().run(suite)

    assert 'Falsifying example' not in o.getvalue()
