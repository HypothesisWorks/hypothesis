# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

import django.test as dt
from hypothesis import LifeCycle


class DjangoLifecycle(LifeCycle):
    def __init__(self, test_case):
        self.__test_case = test_case

    def setup_example(self):
        self.__test_case._pre_setup()

    def teardown_example(self, example):
        self.__test_case._post_teardown()


class HypothesisTestCase(object):
    def hypothesis_lifecycle_definition(self):
        return DjangoLifecycle(self)

    def __call__(self, result=None):
        testMethod = getattr(self, self._testMethodName)
        if getattr(testMethod, u'is_hypothesis_test', False):
            return unittest.TestCase.__call__(self, result)
        else:
            return dt.SimpleTestCase.__call__(self, result)


class TestCase(HypothesisTestCase, dt.TestCase):
    pass


class TransactionTestCase(HypothesisTestCase, dt.TransactionTestCase):
    pass
