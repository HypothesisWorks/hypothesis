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

from unittest import TestCase as VanillaTestCase

from django.db import IntegrityError
from hypothesis import given
from hypothesis.strategies import integers
from hypothesis.extra.django import TestCase, TransactionTestCase
from tests.django.toystore.models import Company


class SomeStuff(object):

    @given(integers())
    def test_is_blank_slate(self, unused):
        Company.objects.create(name=u'MickeyCo')

    def test_normal_test_1(self):
        Company.objects.create(name=u'MickeyCo')

    def test_normal_test_2(self):
        Company.objects.create(name=u'MickeyCo')


class TestConstraintsWithTransactions(SomeStuff, TestCase):
    pass


class TestConstraintsWithoutTransactions(SomeStuff, TransactionTestCase):
    pass


class TestWorkflow(VanillaTestCase):

    def test_does_not_break_later_tests(self):
        def break_the_db(i):
            Company.objects.create(name=u'MickeyCo')
            Company.objects.create(name=u'MickeyCo')

        class LocalTest(TestCase):

            @given(integers().map(break_the_db))
            def test_does_not_break_other_things(self, unused):
                pass

            def test_normal_test_1(self):
                Company.objects.create(name=u'MickeyCo')

        t = LocalTest(u'test_normal_test_1')
        try:
            t.test_does_not_break_other_things()
        except IntegrityError:
            pass
        t.test_normal_test_1()
