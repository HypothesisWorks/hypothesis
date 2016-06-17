from datetime import date, datetime, time
from decimal import Decimal

from django.core.validators import EmailValidator, URLValidator
from django.utils import six

from hypothesis import given
from hypothesis.extra.django import TestCase, TransactionTestCase
from hypothesis.extra.django.models import models

from tests.django.test_app.models import TestModel


class ModelsTest(TestCase):

    @given(models(TestModel))
    def testModelFieldTypes(self, obj):
        self.assertIsInstance(obj.big_integer_field, int)
        self.assertIsInstance(obj.binary_field, six.binary_type)
        self.assertIsInstance(obj.boolean_field, bool)
        self.assertIsInstance(obj.char_field, six.text_type)
        self.assertIsInstance(obj.date_field, date)
        self.assertIsInstance(obj.datetime_field, datetime)
        self.assertIsInstance(obj.decimal_field, Decimal)
        self.assertIsInstance(obj.email_field, six.text_type)
        EmailValidator()(obj.email_field)
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
        URLValidator()(obj.url_field)


# Tests for the functionality of the Django TestCase derivatives.

class TestCaseTestBase(object):

    def testNonHypothesisTest(self):
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
