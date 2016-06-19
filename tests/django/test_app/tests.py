# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from hypothesis import given, strategies as st, settings, HealthCheck
from hypothesis.extra.django import TestCase, TransactionTestCase
from hypothesis.extra.django.models import models, default_value
from hypothesis.internal.compat import hrange

from tests.django.test_app.models import TestModel


allow_slow = settings(
    suppress_health_check=[HealthCheck.too_slow],
)


class ModelsTest(TestCase):

    multi_db = True

    def assertTestModel(self, obj):
        self.assertIsInstance(obj, TestModel)
        # Our aim is to generate valid Django models. Django's validation is
        # better than anything we can specify here, and will catch any issues
        # with our field strategies.
        obj.full_clean()

    @given(models(TestModel))
    @allow_slow
    def testCanGenerateModels(self, obj):
        self.assertTestModel(obj)

    @given(models(TestModel, char_field_default=default_value))
    @allow_slow
    def testCanGenerateModelsDefaultValues(self, obj):
        self.assertTestModel(obj)
        self.assertEqual(obj.char_field_default, "default_value")

    @given(models(TestModel, char_field=st.just("field_override")))
    @allow_slow
    def testCanGenerateModelsFieldOverrides(self, obj):
        self.assertTestModel(obj)
        self.assertEqual(obj.char_field, "field_override")

    @given(models(TestModel, char_field=st.sampled_from(("", "value",))))
    @settings(
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.filter_too_much,
        ],
    )
    def testCanGenerateModelsFieldOverridesInvalidValues(self, obj):
        self.assertTestModel(obj)
        # All blank values will be filtered out.
        self.assertEqual(obj.char_field, "value")

    @given(models(TestModel, foreign_key_field=models(TestModel)))
    @allow_slow
    def testCanGenerateModelsForeignKeyOverrides(self, obj):
        self.assertTestModel(obj)
        self.assertTestModel(obj.foreign_key_field)

    @given(models(TestModel, __db=st.just("extra")))
    @allow_slow
    def testCanGenerateModelsSingleDb(self, obj):
        self.assertTestModel(obj)
        self.assertEqual(TestModel.objects.using("extra").count(), 1)

    @given(models(TestModel, __db=st.sampled_from(("default", "extra"))))
    @allow_slow
    def testCanGenerateModelsMultiDb(self, obj):
        self.assertTestModel(obj)

    def testCanGenerateExamples(self):
        for n in hrange(10):
            obj = models(TestModel).example()
            self.assertTestModel(obj)
            self.assertEqual(TestModel.objects.count(), n + 1)


# Tests for the functionality of the Django TestCase derivatives.

class TestCaseTestBase(object):

    def testDatabaseRollbackNonHypothesis(self):
        self.assertEqual(TestModel.objects.count(), 0)
        # Easiest way to create a TestModel instance!
        models(TestModel).example()
        self.assertEqual(TestModel.objects.count(), 1)

    @given(models(TestModel))
    @allow_slow
    def testDatabaseRollback(self, obj):
        self.assertEqual(TestModel.objects.count(), 1)

    @classmethod
    def tearDownClass(cls):
        super(TestCaseTestBase, cls).tearDownClass()
        # If the test methods cleaned up correctly, then there will
        # be no TestModel instances in the database. Can't use
        # assertEqual(), however, as there is no longer any self!
        assert TestModel.objects.count() == 0


class TestCaseTest(TestCaseTestBase, TestCase):

    pass


class TransactionTestCaseTest(TestCaseTestBase, TransactionTestCase):

    pass
