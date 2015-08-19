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

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
from hypothesis import given
from faker.providers import BaseProvider
from hypothesis.strategytests import strategy_test_suite
from hypothesis.internal.debug import minimal
from hypothesis.searchstrategy import strategy
from hypothesis.extra.fakefactory import fake_factory


class KittenProvider(BaseProvider):

    def kittens(self):
        return 'meow %d' % (self.random_number(digits=10),)


@given(fake_factory('kittens', providers=[KittenProvider]))
def test_kittens_meow(kitten):
    assert 'meow' in kitten


@given(fake_factory('email'))
def test_email(email):
    assert '@' in email


@given(fake_factory('name', locale='en_US'))
def test_english_names_are_ascii(name):
    name.encode('ascii')


def test_french_names_may_have_an_accent():
    minimal(
        fake_factory('name', locale='fr_FR'),
        lambda x: 'é' not in x
    )


def test_fake_factory_errors_with_both_locale_and_locales():
    with pytest.raises(ValueError):
        fake_factory(
            'name', locale='fr_FR', locales=['fr_FR', 'en_US']
        )


def test_fake_factory_errors_with_unsupported_locale():
    with pytest.raises(ValueError):
        fake_factory(
            'name', locale='badger_BADGER'
        )


def test_factory_errors_with_source_for_unsupported_locale():
    with pytest.raises(ValueError):
        fake_factory('state', locale='ja_JP')


def test_fake_factory_errors_if_any_locale_is_unsupported():
    with pytest.raises(ValueError):
        fake_factory(
            'name', locales=['fr_FR', 'en_US', 'mushroom_MUSHROOM']
        )


def test_fake_factory_errors_if_unsupported_method():
    with pytest.raises(ValueError):
        fake_factory('spoon')


def test_fake_factory_errors_if_private_ish_method():
    with pytest.raises(ValueError):
        fake_factory('_Generator__config')


def test_can_get_specification_for_fake_factory():
    ff = fake_factory('email')
    strategy(ff)


TestFakeEmail = strategy_test_suite(
    fake_factory('email')
)

TestFakeNames = strategy_test_suite(
    fake_factory('name')
)

TestFakeEnglishNames = strategy_test_suite(
    fake_factory('name', locale='en_US')
)

TestStates = strategy_test_suite(
    fake_factory('state')
)
