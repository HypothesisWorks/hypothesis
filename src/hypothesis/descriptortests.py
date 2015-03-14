# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""Support for testing your custom implementations of descriptors."""

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from random import Random
from unittest import TestCase
from collections import namedtuple

from hypothesis import Verifier, Exhausted, given
from hypothesis.database import ExampleDatabase
from hypothesis.settings import Settings
from hypothesis.searchstrategy import BuildContext, SearchStrategy, \
    strategy
from hypothesis.internal.compat import text_type, integer_types
from hypothesis.internal.fixers import nice_string, actually_equal
from hypothesis.database.backend import SQLiteBackend
from hypothesis.internal.hashitanyway import hash_everything

TemplatesFor = namedtuple('TemplatesFor', ('base',))


class TemplatesStrategy(SearchStrategy):

    def __init__(self, base_strategy):
        super(TemplatesStrategy, self).__init__()
        self.descriptor = TemplatesFor(base_strategy.descriptor)
        self.base_strategy = base_strategy
        self.size_lower_bound = base_strategy.size_lower_bound
        self.size_upper_bound = base_strategy.size_upper_bound

    def produce_parameter(self, random):
        return self.base_strategy.produce_parameter(random)

    def produce_template(self, context, pv):
        return self.base_strategy.produce_template(context, pv)

    def reify(self, template):
        return template

    def to_basic(self, template):
        return self.base_strategy.to_basic(template)

    def from_basic(self, data):
        return self.base_strategy.from_basic(data)

    def simplify(self, template):
        return self.base_strategy.simplify(template)


@strategy.extend(TemplatesFor)
def templates_for(descriptor, settings):
    return TemplatesStrategy(strategy(descriptor.base, settings))


def descriptor_test_suite(
    descriptor,
    max_examples=100, random=None
):
    settings = Settings(
        database=None,
        max_examples=max_examples,
        average_list_length=2.0,
    )
    random = random or Random()
    verifier = Verifier(
        settings=settings,
        random=random
    )
    strat = strategy(descriptor, settings)
    descriptor_test = given(
        TemplatesFor(descriptor), verifier=verifier
    )

    class ValidationSuite(TestCase):

        def __repr__(self):
            return 'descriptor_test_suite(%s)' % (
                nice_string(descriptor),
            )

        @given(descriptor, verifier=verifier)
        def test_does_not_error(self, value):
            pass

        @descriptor_test
        def test_two_reifications_are_equal(self, template):
            assert actually_equal(
                strat.reify(template),
                strat.reify(template),
            )

        @descriptor_test
        def test_is_basic(self, value):
            def is_basic(v):
                return isinstance(
                    v, integer_types + (list, type(None), text_type)
                ) and (
                    not isinstance(v, list) or
                    all(is_basic(w) for w in v)
                )
            supposedly_basic = strat.to_basic(value)
            self.assertTrue(is_basic(supposedly_basic), repr(supposedly_basic))

        def test_produces_two_distinct_hashes(self):
            try:
                verifier.falsify(
                    lambda x, y: hash_everything(x) == hash_everything(y),
                    descriptor, descriptor)
            except Exhausted:
                pass

        @descriptor_test
        def test_can_round_trip_through_the_database(self, template):
            empty_db = ExampleDatabase(
                backend=SQLiteBackend(':memory:'),
            )
            storage = empty_db.storage_for(descriptor)
            storage.save(template)
            values = list(storage.fetch())
            assert len(values) == 1
            assert actually_equal(template, values[0])

        @descriptor_test
        def test_can_minimize_to_empty(self, template):
            simplest = list(strat.simplify_such_that(
                template, lambda x: True
            ))[-1]
            assert list(strat.simplify(simplest)) == []

        @given(Random, verifier=verifier)
        def test_can_perform_all_basic_operations(self, random):
            parameter = strat.draw_parameter(random)
            template = strat.draw_template(BuildContext(random), parameter)
            minimal_template = list(strat.simplify_such_that(
                template,
                lambda x: True
            ))[-1]
            strat.reify(minimal_template)
            assert actually_equal(
                minimal_template,
                strat.from_basic(strat.to_basic(minimal_template))
            )
            list(strat.decompose(minimal_template))

    return ValidationSuite
