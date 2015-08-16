# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

from hypothesis import given, assume
from hypothesis.errors import InvalidArgument
from hypothesis.strategies import just, lists
from hypothesis.extra.django import TestCase, TransactionTestCase
from tests.django.toystore.models import Store, Company, Customer, \
    ManyInts, SelfLoop, Customish, CustomishField, CouldBeCharming
from hypothesis.extra.django.models import models, \
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

    @given(lists(models(ManyInts)))
    def test_no_overflow_in_integer(self, manyints):
        pass

    @given(models(Customish))
    def test_custom_field(self, x):
        assert x.customish == u'a'

    def test_mandatory_fields_are_mandatory(self):
        self.assertRaises(InvalidArgument, models, Store)


class TestsNeedingRollback(TransactionTestCase):

    def test_can_get_examples(self):
        for _ in range(200):
            models(Company).example()
