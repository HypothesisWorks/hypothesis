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
from hypothesis.descriptors import one_of
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import text_type, integer_types
from hypothesis.database.backend import SQLiteBackend
from hypothesis.searchstrategy.table import StrategyTable
from hypothesis.internal.utils.fixers import nice_string, actually_equal
from hypothesis.internal.utils.hashitanyway import hash_everything

TemplatesFor = namedtuple('TemplatesFor', ('base',))


class TemplatesStrategy(SearchStrategy):

    def __init__(self, base_strategy):
        super(TemplatesStrategy, self).__init__()
        self.descriptor = TemplatesFor(base_strategy.descriptor)
        self.base_strategy = base_strategy
        self.parameter = base_strategy.parameter
        self.size_lower_bound = base_strategy.size_lower_bound
        self.size_upper_bound = base_strategy.size_upper_bound

    def produce_template(self, random, pv):
        return self.base_strategy.produce_template(random, pv)

    def reify(self, template):
        return template

    def to_basic(self, template):
        return self.base_strategy.to_basic(template)

    def from_basic(self, data):
        return self.base_strategy.from_basic(data)

    def simplify(self, template):
        return self.base_strategy.simplify(template)


StrategyTable.default().define_specification_for_instances(
    TemplatesFor,
    lambda s, d: TemplatesStrategy(s.specification_for(d.base))
)


def descriptor_test_suite(
    descriptor, strategy_table=None,
    max_examples=100, random=None
):
    strategy_table = strategy_table or StrategyTable()
    settings = Settings(
        database=None,
        max_examples=max_examples,
    )
    random = random or Random()
    verifier = Verifier(
        settings=settings,
        strategy_table=strategy_table,
        random=random
    )
    strategy = strategy_table.strategy(descriptor)
    mixed = one_of((int, (bool, str), descriptor))
    mixed_strategy = strategy_table.strategy(mixed)
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
                strategy.reify(template),
                strategy.reify(template),
            )

        @given(TemplatesFor(mixed), verifier=verifier)
        def test_can_simplify_mixed(self, template):
            list(mixed_strategy.simplify_such_that(template, lambda x: True))

        @descriptor_test
        def test_is_basic(self, value):
            def is_basic(v):
                if not isinstance(
                    v, integer_types + (list, type(None), text_type)
                ):
                    return False
                if isinstance(v, list):
                    return all(is_basic(w) for w in v)
                else:
                    return True
            supposedly_basic = strategy.to_basic(value)
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
                strategies=strategy_table,
            )
            storage = empty_db.storage_for(descriptor)
            storage.save(template)
            values = list(storage.fetch())
            assert len(values) == 1
            assert actually_equal(template, values[0])

        @descriptor_test
        def test_can_minimize_to_empty(self, template):
            simplest = list(strategy.simplify_such_that(
                template, lambda x: True
            ))[-1]
            assert list(strategy.simplify(simplest)) == []

        @given(Random, verifier=verifier)
        def test_can_perform_all_basic_operations(self, random):
            parameter = strategy.parameter.draw(random)
            template = strategy.produce_template(random, parameter)
            minimal_template = list(strategy.simplify_such_that(
                template,
                lambda x: True
            ))[-1]
            strategy.reify(minimal_template)
            assert actually_equal(
                minimal_template,
                strategy.from_basic(strategy.to_basic(minimal_template))
            )
            list(strategy.decompose(minimal_template))

#       @descriptor_test
#       def test_can_decompose(self, template):
#           list(strategy.decompose(template))

    return ValidationSuite
