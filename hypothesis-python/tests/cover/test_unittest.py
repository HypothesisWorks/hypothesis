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

import io
import unittest

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import FailedHealthCheck, HypothesisWarning
from hypothesis.internal.compat import PY2
from tests.common.utils import fails_with


class Thing_with_a_subThing(unittest.TestCase):
    """Example test case using subTest for the actual test below."""

    @given(st.tuples(st.booleans(), st.booleans()))
    def thing(self, lst):
        for i, b in enumerate(lst):
            with pytest.warns(HypothesisWarning):
                with self.subTest((i, b)):
                    self.assertTrue(b)


def test_subTest():
    suite = unittest.TestSuite()
    suite.addTest(Thing_with_a_subThing("thing"))
    stream = io.BytesIO() if PY2 else io.StringIO()
    out = unittest.TextTestRunner(stream=stream).run(suite)
    assert len(out.failures) <= out.testsRun, out


class test_given_on_setUp_fails_health_check(unittest.TestCase):
    @fails_with(FailedHealthCheck)
    @given(st.integers())
    def setUp(self, i):
        pass

    def test(self):
        """Provide something to set up for, so the setUp method is called."""
        pass
