# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis import given
from toystore.models import Company
from hypothesis.extra.django import TestCase, TransactionTestCase


class SomeStuff(object):

    @given(int)
    def test_is_blank_slate(self, unused):
        Company.objects.create(name='MickeyCo')

    def test_normal_test_1(self):
        Company.objects.create(name='MickeyCo')

    def test_normal_test_2(self):
        Company.objects.create(name='MickeyCo')


class TestConstraintsWithTransactions(SomeStuff, TestCase):
    pass


class TestConstraintsWithoutTransactions(SomeStuff, TransactionTestCase):
    pass
