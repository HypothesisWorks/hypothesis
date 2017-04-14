# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

import random as globalrandom
from random import Random

import faker
from faker.factory import AVAILABLE_LOCALES

from hypothesis.internal.compat import text_type
from hypothesis.internal.reflection import check_valid_identifier
from hypothesis.searchstrategy.strategies import SearchStrategy


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

    def do_draw(self, data):
        seed = data.draw_bytes(4)
        random = Random(bytes(seed))
        return self.gen_example(random)

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

    def gen_example(self, random):
        factory = self.factory_for(random.choice(self.locales))
        original = globalrandom.getstate()
        seed = random.getrandbits(128)
        try:
            factory.seed(seed)
            return text_type(getattr(factory, self.source)())
        finally:
            globalrandom.setstate(original)
