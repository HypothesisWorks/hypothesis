from datetime import date, datetime, time
from decimal import Decimal

from django.utils import six

from hypothesis import given, strategies as st
from hypothesis.extra.django import TestCase, TransactionTestCase
from hypothesis.extra.django.models import models
from hypothesis.internal.compat import hrange

from tests.django.test_app.models import TestModel


class ModelsTest(TestCase):

    multi_db = True

    def assertTestModel(self, obj):
        self.assertIsInstance(obj, TestModel)
        # Rather than test field values individually, just let Django test it
        # for us!
        obj.full_clean()
        # But lets's also sanity check the field types, just to be on the
        # safe side...
        self.assertIsInstance(obj.big_integer_field, int)
        self.assertIsInstance(obj.binary_field, six.binary_type)
        self.assertIsInstance(obj.boolean_field, bool)
        self.assertIsInstance(obj.char_field, six.text_type)
        self.assertIsInstance(obj.char_field_blank, six.text_type)
        self.assertIsInstance(obj.char_field_default, six.text_type)
        self.assertIsInstance(obj.char_field_none, (six.text_type, type(None)))
        self.assertIsInstance(obj.char_field_unique, six.text_type)
        self.assertIsInstance(obj.date_field, date)
        self.assertIsInstance(obj.datetime_field, datetime)
        self.assertIsInstance(obj.decimal_field, Decimal)
        self.assertIsInstance(obj.email_field, six.text_type)
        self.assertIsInstance(obj.email_field_blank, six.text_type)
        self.assertIsInstance(obj.email_field_max_length, six.text_type)
        self.assertIsInstance(obj.float_field, float)
        self.assertIsInstance(obj.integer_field, int)
        self.assertIsInstance(obj.null_boolean_field, (bool, type(None)))
        self.assertIsInstance(obj.positive_integer_field, int)
        self.assertIsInstance(obj.positive_small_integer_field, int)
        self.assertIsInstance(obj.slug_field, six.text_type)
        self.assertIsInstance(obj.small_integer_field, int)
        self.assertIsInstance(obj.text_field, six.text_type)
        self.assertIsInstance(obj.time_field, time)
        self.assertIsInstance(obj.url_field, six.text_type)

    @given(models(TestModel))
    def testCanGenerateModels(self, obj):
        self.assertTestModel(obj)

    @given(models(TestModel, __db=st.just("extra")))
    def testCanGenerateModelsSingleDb(self, obj):
        self.assertTestModel(obj)
        self.assertEqual(TestModel.objects.using("extra").count(), 1)

    @given(models(TestModel, __db=st.sampled_from(("default", "extra"))))
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
