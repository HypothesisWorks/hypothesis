# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis.extra.django import TestCase, TransactionTestCase
from hypothesis.extra.django.models import ModelNotSupported
from hypothesis import given, assume, strategy
from toystore.models import Company, Customer, CouldBeCharming, Store, \
    SelfLoop, LoopA, LoopB, ManyInts
from unittest import TestCase as VanillaTestCase


class TestGetsBasicModels(TestCase):
    @given(Company)
    def test_is_company(self, company):
        self.assertIsInstance(company, Company)
        self.assertIsNotNone(company.pk)

    @given(Store)
    def test_can_get_a_store(self, store):
        assert store.company.pk

    @given([Company])
    def test_can_get_multiple_models_with_unique_field(self, companies):
        assume(len(companies) > 1)
        for c in companies:
            self.assertIsNotNone(c.pk)
        self.assertEqual(
            len(companies), len({c.name for c in companies})
        )

    @given(Customer)
    def test_is_customer(self, customer):
        self.assertIsInstance(customer, Customer)
        self.assertIsNotNone(customer.pk)
        self.assertIsNotNone(customer.email)

    @given(CouldBeCharming)
    def test_is_not_charming(self, not_charming):
        self.assertIsInstance(not_charming, CouldBeCharming)
        self.assertIsNotNone(not_charming.pk)
        self.assertIsNone(not_charming.charm)

    @given(SelfLoop)
    def test_sl(self, sl):
        self.assertIsNone(sl.me)

    @given([ManyInts])
    def test_no_overflow_in_integer(self, manyints):
        pass


class TestsNeedingRollback(TransactionTestCase):
    def test_can_get_examples(self):
        for _ in range(200):
            strategy(Company).example()


class TestUnsupportedModels(VanillaTestCase):

    def test_mutual_loop_is_unsupported(self):
        with self.assertRaises(ModelNotSupported):
            strategy(LoopA)

    def test_nullable_loop_is_supported(self):
        strategy(LoopB)
