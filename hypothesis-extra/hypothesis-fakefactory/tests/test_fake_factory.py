# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
from hypothesis import given, falsify
from faker.providers import BaseProvider
from hypothesis.strategytable import StrategyTable
from hypothesis.descriptortests import descriptor_test_suite
from hypothesis.extra.fakefactory import FakeFactory


class KittenProvider(BaseProvider):

    def kittens(self):
        return 'meow %d' % (self.random_number(digits=10),)


def test_produces_any_unicode():
    ff = FakeFactory('email')
    strat = StrategyTable.default().specification_for(ff)
    assert strat.could_have_produced('foo')
    assert not strat.could_have_produced(b'foo')


@given(FakeFactory('kittens', providers=[KittenProvider]))
def test_kittens_meow(kitten):
    assert 'meow' in kitten


@given(FakeFactory('email'))
def test_email(email):
    assert '@' in email


@given(FakeFactory('name', locale='en_US'))
def test_english_names_are_ascii(name):
    name.encode('ascii')


def test_french_names_may_have_an_accent():
    falsify(
        lambda x: 'é' not in x,
        FakeFactory('name', locale='fr_FR')
    )


def test_fake_factory_errors_with_both_locale_and_locales():
    with pytest.raises(ValueError):
        FakeFactory(
            'name', locale='fr_FR', locales=['fr_FR', 'en_US']
        )


def test_fake_factory_errors_with_unsupported_locale():
    with pytest.raises(ValueError):
        FakeFactory(
            'name', locale='badger_BADGER'
        )


def test_fake_factory_errors_if_any_locale_is_unsupported():
    with pytest.raises(ValueError):
        FakeFactory(
            'name', locales=['fr_FR', 'en_US', 'mushroom_MUSHROOM']
        )


def test_fake_factory_errors_if_unsupported_method():
    with pytest.raises(ValueError):
        FakeFactory('spoon')


def test_fake_factory_errors_if_private_ish_method():
    with pytest.raises(ValueError):
        FakeFactory('_Generator__config')


def test_can_get_specification_for_fake_factory():
    ff = FakeFactory('email')
    strat = StrategyTable.default().specification_for(ff)
    assert strat.descriptor == ff


TestFakeEmail = descriptor_test_suite(
    FakeFactory('email')
)

TestFakeNames = descriptor_test_suite(
    FakeFactory('name')
)

TestFakeEnglishNames = descriptor_test_suite(
    FakeFactory('name', locale='en_US')
)
