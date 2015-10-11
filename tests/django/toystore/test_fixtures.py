# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

from django.test import TestCase

from hypothesis.strategies import just, lists
from tests.django.toystore.models import Store, Company, Customer
from hypothesis.extra.django.models import models
from hypothesis.extra.django.fixtures import fixture

a_company = fixture(
    models(Company),
    lambda c: c.name,
)

a_different_company = fixture(
    models(Company),
    lambda c: len(c.name) > len(a_company().name)
)

another_company = fixture(
    models(Company),
    lambda c: c.name,
)

some_companies = fixture(
    lists(models(Company)),
    lambda ls: len({c.pk for c in ls}) >= 5
)


def with_some_stores(company):
    child_strategy = lists(
        models(Store, company=just(company)), min_size=1
    )
    return child_strategy.map(lambda _: company)

a_company_with_some_stores = fixture(
    models(Company).flatmap(with_some_stores),
    lambda x: x.store_set.count() >= 2
)

a_gendered_customer = fixture(
    models(Customer),
    lambda c: c.name and c.gender
)


class TestFinding(TestCase):

    def test_can_find_unique_name(self):
        assert len(a_company().name) == 1

    def test_can_reference_a_fixture_from_within_a_fixture(self):
        assert len(a_different_company().name) > len(a_company().name)

    def test_same_fixture_twice_is_same_object(self):
        assert a_company().pk == a_company().pk

    def test_different_fixtures_with_same_constraint_are_different(self):
        assert a_company().name != another_company().name

    def test_can_get_multiple_companies(self):
        assert len(some_companies()) == 5

    def test_can_find_with_multiple_unique(self):
        x = a_gendered_customer()
        self.assertEqual(u'0', x.name)
        self.assertEqual(u'0', x.gender)

    def test_can_find_with_children(self):
        x = a_company_with_some_stores()
        assert len(x.store_set.all()) == 2
