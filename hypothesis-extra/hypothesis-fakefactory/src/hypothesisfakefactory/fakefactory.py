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
    check_data_type


def fake_factory(source, locale=None, locales=None, providers=()):
    test_faker = faker.Faker()

    for provider in providers:
        test_faker.add_provider(provider)

    if not hasattr(test_faker, source) or source[0] == '_':
        raise ValueError('No such source %r' % (source,))
    if locale is not None and locales is not None:
        raise ValueError('Cannot specify both single and multiple locales')
    if locale:
        locales = (locale,)
    elif locales:
        locales = tuple(locales)
    else:
        locales = None
    for l in (locales or ()):
        if l not in AVAILABLE_LOCALES:
            raise ValueError('Unsupported locale %r' % (l,))
    locales = locales or AVAILABLE_LOCALES
    return FakeFactoryStrategy(source, providers, locales)


class FakeFactoryStrategy(SearchStrategy):

    def __init__(self, source, providers, locales):
        self.source = source
        self.providers = tuple(providers)
        self.locales = tuple(locales)

    def draw_parameter(self, random):
        return dist.non_empty_subset(random, self.locales)

    def draw_template(self, context, pv):
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
