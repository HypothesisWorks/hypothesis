# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

import pytest
from faker.providers import BaseProvider

from hypothesis import given
from tests.common.debug import minimal
from tests.common.utils import checks_deprecated_behaviour
from hypothesis.extra.fakefactory import fake_factory


class KittenProvider(BaseProvider):

    def kittens(self):
        return u'meow %d' % (self.random_number(digits=10),)


@checks_deprecated_behaviour
def test_kittens_meow():
    @given(fake_factory(u'kittens', providers=[KittenProvider]))
    def inner(kitten):
        assert u'meow' in kitten

    inner()


@checks_deprecated_behaviour
def test_email():
    @given(fake_factory(u'email'))
    def inner(email):
        assert u'@' in email

    inner()


@checks_deprecated_behaviour
def test_english_names_are_ascii():
    @given(fake_factory(u'name', locale=u'en_US'))
    def inner(name):
        name.encode(u'ascii')

    inner()


@checks_deprecated_behaviour
def test_french_names_may_have_an_accent():
    minimal(
        fake_factory(u'name', locale=u'fr_FR'),
        lambda x: u'é' not in x
    )


@checks_deprecated_behaviour
def test_fake_factory_errors_with_both_locale_and_locales():
    with pytest.raises(ValueError):
        fake_factory(
            u'name', locale=u'fr_FR', locales=[u'fr_FR', u'en_US']
        )


@checks_deprecated_behaviour
def test_fake_factory_errors_with_unsupported_locale():
    with pytest.raises(ValueError):
        fake_factory(
            u'name', locale=u'badger_BADGER'
        )


@checks_deprecated_behaviour
def test_factory_errors_with_source_for_unsupported_locale():
    with pytest.raises(ValueError):
        fake_factory(u'state', locale=u'ja_JP')


@checks_deprecated_behaviour
def test_fake_factory_errors_if_any_locale_is_unsupported():
    with pytest.raises(ValueError):
        fake_factory(
            u'name', locales=[u'fr_FR', u'en_US', u'mushroom_MUSHROOM']
        )


@checks_deprecated_behaviour
def test_fake_factory_errors_if_unsupported_method():
    with pytest.raises(ValueError):
        fake_factory(u'spoon')


@checks_deprecated_behaviour
def test_fake_factory_errors_if_private_ish_method():
    with pytest.raises(ValueError):
        fake_factory(u'_Generator__config')
