# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import faker
import hypothesis.params as params
from faker.config import AVAILABLE_LOCALES
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import text_type


class FakeFactory(object):

    def __init__(self, source, locale=None, locales=None, providers=()):
        test_faker = faker.Faker()

        for provider in providers:
            test_faker.add_provider(provider)

        self.source = source
        if not hasattr(test_faker, source) or source[0] == '_':
            raise ValueError('No such source %r' % (source,))
        if locale is not None and locales is not None:
            raise ValueError('Cannot specify both single and multiple locales')
        if locale:
            self.locales = (locale,)
        elif locales:
            self.locales = tuple(locales)
        else:
            self.locales = None
        if self.locales:
            for l in self.locales:
                if l not in AVAILABLE_LOCALES:
                    raise ValueError('Unsupported locale %r' % (l,))
        self.providers = tuple(providers)


class FakeFactoryStrategy(SearchStrategy):

    def __init__(self, details):
        self.descriptor = details
        self.source = details.source
        self.parameter = params.CompositeParameter(
            locales=params.NonEmptySubset(
                details.locales or AVAILABLE_LOCALES
            )
        )
        self.providers = details.providers

    def produce_template(self, random, pv):
        factory = faker.Faker(locale=random.choice(pv.locales))
        factory.seed(random.getrandbits(128))
        for p in self.providers:
            factory.add_provider(p)
        return text_type(getattr(factory, self.source)())

    def could_have_produced(self, value):
        return isinstance(value, text_type)
