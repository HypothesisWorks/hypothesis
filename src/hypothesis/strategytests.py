# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""Support for testing your custom implementations of specifiers."""

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from random import Random
from unittest import TestCase
from collections import namedtuple

from hypothesis import given
from hypothesis.database import ExampleDatabase
from hypothesis.settings import Settings
from hypothesis.utils.show import show
from hypothesis.internal.compat import text_type, integer_types
from hypothesis.database.backend import SQLiteBackend
from hypothesis.internal.verifier import Verifier
from hypothesis.searchstrategy.strategies import BuildContext, \
    SearchStrategy, strategy

TemplatesFor = namedtuple('TemplatesFor', ('base',))


class TemplatesStrategy(SearchStrategy):

    def __init__(self, base_strategy):
        super(TemplatesStrategy, self).__init__()
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
def templates_for(specifier, settings):
    return TemplatesStrategy(strategy(specifier.base, settings))


def strategy_test_suite(
    specifier,
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
    strat = strategy(specifier, settings)
    specifier_test = given(
        TemplatesFor(specifier), settings=settings
    )

    class ValidationSuite(TestCase):

        def __repr__(self):
            return 'strategy_test_suite(%s)' % (
                show(specifier),
            )

        @given(specifier, settings=settings)
        def test_does_not_error(self, value):
            pass

        def test_can_give_example(self):
            strat.example()

        @specifier_test
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

        @specifier_test
        def test_can_round_trip_through_the_database(self, template):
            empty_db = ExampleDatabase(
                backend=SQLiteBackend(':memory:'),
            )
            try:
                storage = empty_db.storage_for(specifier)
                storage.save(template)
                values = list(storage.fetch())
                assert len(values) == 1
                assert strat.to_basic(template) == strat.to_basic(values[0])
            finally:
                empty_db.close()

        @specifier_test
        def test_template_is_hashable(self, template):
            hash(template)

        @specifier_test
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
            assert (
                strat.to_basic(minimal_template) ==
                strat.to_basic(
                    strat.from_basic(strat.to_basic(minimal_template)))
            )

    return ValidationSuite
