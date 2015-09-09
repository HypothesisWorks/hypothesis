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

from random import Random

import faker
import hypothesis.internal.distributions as dist
from faker.factory import AVAILABLE_LOCALES
from hypothesis.internal.compat import hrange, text_type
from hypothesis.internal.reflection import check_valid_identifier
from hypothesis.internal.distributions import geometric
from hypothesis.searchstrategy.strategies import SearchStrategy, \
    check_data_type


def fake_factory(source, locale=None, locales=None, providers=()):
    check_valid_identifier(source)
    if source[0] == u'_':
        raise ValueError(u'Bad source name %s' % (source,))

    if locale is not None and locales is not None:
        raise ValueError(u'Cannot specify both single and multiple locales')
    if locale:
        locales = (locale,)
    elif locales:
        locales = tuple(locales)
    else:
        locales = None
    for l in (locales or ()):
        if l not in AVAILABLE_LOCALES:
            raise ValueError(u'Unsupported locale %r' % (l,))

    def supports_source(locale):
        test_faker = faker.Faker(locale)
        for provider in providers:
            test_faker.add_provider(provider)
        return hasattr(test_faker, source)

    if locales is None:
        locales = list(filter(supports_source, AVAILABLE_LOCALES))
        if not locales:
            raise ValueError(u'No such source %r' % (source,))
    else:
        for l in locales:
            if not supports_source(locale):
                raise ValueError(u'Unsupported source %s for locale %s' % (
                    source, l
                ))
    return FakeFactoryStrategy(source, providers, locales)


class FakeFactoryStrategy(SearchStrategy):

    def __init__(self, source, providers, locales):
        self.source = source
        self.providers = tuple(providers)
        self.locales = tuple(locales)
        self.factories = {}

    def draw_parameter(self, random):
        locales = dist.non_empty_subset(random, self.locales)
        n = 1 + geometric(random, 0.1)
        return [
            self.gen_example(random, locales)
            for _ in hrange(n)
        ]

    def factory_for(self, locale):
        try:
            return self.factories[locale]
        except KeyError:
            pass
        factory = faker.Faker(locale=locale)
        self.factories[locale] = factory
        for p in self.providers:
            factory.add_provider(p)
        return factory

    def gen_example(self, random, locales):
        factory = self.factory_for(random.choice(locales))
        factory.seed(random.getrandbits(128))
        return text_type(getattr(factory, self.source)())

    def basic_simplify(self, random, template):
        for _ in hrange(10):
            y = self.gen_example(
                Random(template.encode(u'utf-8')), self.locales)
            if self.strictly_simpler(y, template):
                yield y

    def strictly_simpler(self, x, y):
        return (len(x), x) < (len(y), y)

    def draw_template(self, random, pv):
        return random.choice(pv)

    def reify(self, template):
        return template

    def to_basic(self, value):
        return value

    def from_basic(self, value):
        check_data_type(text_type, value)
        return value
