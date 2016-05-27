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

from hypothesis import given, assume
from hypothesis.errors import InvalidArgument
from hypothesis.strategies import just, lists
from hypothesis.extra.django import TestCase, TransactionTestCase
from tests.django.toystore.models import Store, Company, Customer, \
    SelfLoop, Customish, ManyNumerics, CustomishField, CouldBeCharming, \
    CustomishDefault, RestrictedFields, MandatoryComputed
from hypothesis.extra.django.models import models, default_value, \
    add_default_field_mapping

add_default_field_mapping(CustomishField, just(u'a'))


class TestGetsBasicModels(TestCase):

    @given(models(Company))
    def test_is_company(self, company):
        self.assertIsInstance(company, Company)
        self.assertIsNotNone(company.pk)

    @given(models(Store, company=models(Company)))
    def test_can_get_a_store(self, store):
        assert store.company.pk

    @given(lists(models(Company)))
    def test_can_get_multiple_models_with_unique_field(self, companies):
        assume(len(companies) > 1)
        for c in companies:
            self.assertIsNotNone(c.pk)
        self.assertEqual(
            len({c.pk for c in companies}), len({c.name for c in companies})
        )

    @given(models(Customer))
    def test_is_customer(self, customer):
        self.assertIsInstance(customer, Customer)
        self.assertIsNotNone(customer.pk)
        self.assertIsNotNone(customer.email)

    @given(models(CouldBeCharming))
    def test_is_not_charming(self, not_charming):
        self.assertIsInstance(not_charming, CouldBeCharming)
        self.assertIsNotNone(not_charming.pk)
        self.assertIsNone(not_charming.charm)

    @given(models(SelfLoop))
    def test_sl(self, sl):
        self.assertIsNone(sl.me)

    @given(lists(models(ManyNumerics)))
    def test_no_overflow_in_integer(self, manyints):
        pass

    @given(models(Customish))
    def test_custom_field(self, x):
        assert x.customish == u'a'

    def test_mandatory_fields_are_mandatory(self):
        self.assertRaises(InvalidArgument, models, Store)

    def test_mandatory_computed_fields_are_mandatory(self):
        self.assertRaises(InvalidArgument, models, MandatoryComputed)

    def test_mandatory_computed_fields_may_not_be_provided(self):
        mc = models(MandatoryComputed, company=models(Company))
        self.assertRaises(RuntimeError, mc.example)

    @given(models(MandatoryComputed, company=default_value))
    def test_mandatory_computed_field_default(self, x):
        assert x.company.name == x.name + u'_company'

    @given(models(CustomishDefault))
    def test_customish_default_generated(self, x):
        assert x.customish == u'a'

    @given(models(CustomishDefault, customish=default_value))
    def test_customish_default_not_generated(self, x):
        assert x.customish == u'b'


class TestsNeedingRollback(TransactionTestCase):

    def test_can_get_examples(self):
        for _ in range(200):
            models(Company).example()


class TestRestrictedFields(TestCase):

    @given(models(RestrictedFields))
    def test_constructs_valid_instance(self, instance):
        self.assertTrue(isinstance(instance, RestrictedFields))
        instance.full_clean()
        self.assertLessEqual(len(instance.text_field_4), 4)
        self.assertLessEqual(len(instance.char_field_4), 4)
        self.assertIn(instance.choice_field_text, ('foo', 'bar'))
        self.assertIn(instance.choice_field_int, (1, 2))
        self.assertIn(instance.null_choice_field_int, (1, 2, None))
        self.assertEqual(instance.even_number_field % 2, 0)
        self.assertTrue(instance.non_blank_text_field)
