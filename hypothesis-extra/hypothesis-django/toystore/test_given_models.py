# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis.errors import InvalidArgument
from hypothesis.extra.django import TestCase, TransactionTestCase
from hypothesis.extra.django.models import models, add_default_field_mapping
from hypothesis import given, assume
from toystore.models import Company, Customer, CouldBeCharming, Store, \
    SelfLoop, ManyInts, CustomishField, Customish
from hypothesis.strategies import lists, just

add_default_field_mapping(CustomishField, just("a"))


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
            len(companies), len({c.name for c in companies})
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

    @given(lists(models(ManyInts)))
    def test_no_overflow_in_integer(self, manyints):
        pass

    @given(models(Customish))
    def test_custom_field(self, x):
        assert x.customish == "a"

    def test_mandatory_fields_are_mandatory(self):
        with self.assertRaises(InvalidArgument):
            models(Store)


class TestsNeedingRollback(TransactionTestCase):
    def test_can_get_examples(self):
        for _ in range(200):
            models(Company).example()
