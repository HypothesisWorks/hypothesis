from __future__ import division, print_function, absolute_import, \
    unicode_literals

import django.test as dt
import unittest


class TestCase(dt.TestCase):
    def __call__(self, result=None):
        testMethod = getattr(self, self._testMethodName)
        is_hypothesis = getattr(testMethod, 'is_hypothesis_test', False)
        if is_hypothesis:
            return unittest.TestCase.__call__(self, result)
        else:
            return super(TestCase, self).__call__(result)

    def setup_example(self):
        self._pre_setup()

    def teardown_example(self, example):
        self._post_teardown()
