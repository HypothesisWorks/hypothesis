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
import hypothesis.internal.distributions as dist
from faker import AVAILABLE_LOCALES
from hypothesis.internal.compat import text_type
from hypothesis.searchstrategy.strategies import SearchStrategy, \
    strategy, check_data_type


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

    def __eq__(self, other):
        return (
            type(other) == type(self) and
            self.source == other.source and
            self.locales == other.locales and
            self.providers == other.providers
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((
            type(self), self.source, self.locales
        ))


class FakeFactoryStrategy(SearchStrategy):

    def __init__(self, details):
        self.source = details.source
        self.providers = details.providers
        self.locales = details.locales or AVAILABLE_LOCALES

    def produce_parameter(self, random):
        return dist.non_empty_subset(random, self.locales)

    def produce_template(self, context, pv):
        factory = faker.Faker(locale=context.random.choice(pv))
        factory.seed(context.random.getrandbits(128))
        for p in self.providers:
            factory.add_provider(p)
        return text_type(getattr(factory, self.source)())

    def reify(self, template):
        return template

    def to_basic(self, value):
        return value

    def from_basic(self, value):
        check_data_type(text_type, value)
        return value


@strategy.extend(FakeFactory)
def fake_factory_strategy(d, settings):
    return FakeFactoryStrategy(d)
