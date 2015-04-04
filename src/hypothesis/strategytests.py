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

from hypothesis import given, assume
from hypothesis.errors import Unsatisfiable, BadData
from hypothesis.database import ExampleDatabase
from hypothesis.settings import Settings
from hypothesis.utils.show import show
from hypothesis.utils.extmethod import ExtMethod
from hypothesis.internal.compat import text_type, integer_types
from hypothesis.database.backend import SQLiteBackend
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

    def simplifiers(self, template):
        return self.base_strategy.simplifiers(template)


@strategy.extend(TemplatesFor)
def templates_for(specifier, settings):
    return TemplatesStrategy(strategy(specifier.base, settings))


class Rejected(Exception):
    pass


mess_with_basic_data = ExtMethod()


def mess_with_int(i, random):
    s = random.randint(0, 4)
    if s == 0:
        return -i
    elif s == 1:
        return i + random.randint(-1, 1)
    elif s == 3:
        return i * 2
    elif s == 4:
        b = (2 ** random.randint(31, 129)) + random.randint(-10 ** 5, 10 ** 5)
        if random.randint(0, 1):
            b = -b
        return b

for t in integer_types:
    mess_with_basic_data.extend(t)(mess_with_int)


@mess_with_basic_data.extend(bool)
def mess_with_bool(b, random):
    return bool(random.randint())


@mess_with_basic_data.extend(text_type)
def mess_with_text(text, random):
    if random.randint(0, 1):
        return text.encode('utf-8')
    else:
        return text


@mess_with_basic_data.extend(list)
def mess_with_list(ls, random):
    ls = list(ls)
    if not ls:
        if random.randint(0, 1):
            ls.append(random.randint(-2 ** 128, 2 ** 128))
        return ls
    i = random.randint(0, len(ls))
    if i < len(ls):
        ls[i] = mess_with_basic_data(ls[i], random)
    t = random.randint(0, 5)
    if t == 0:
        while ls and random.randint(0, 1):
            ls.pop()
    elif t == 1:
        j = random.randint(0, len(ls) - 1)
        ls.append(ls[j])
    elif t == 2:
        random.shuffle(ls)
    return ls


@mess_with_basic_data.extend(type(None))
def mess_with_none(n, random):
    if not random.randint(0, 5):
        return float('nan')


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
    strat = strategy(specifier, settings)
    specifier_test = given(
        TemplatesFor(specifier), Random, settings=settings
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

        def test_can_give_list_of_examples(self):
            strategy([strat]).example()

        def test_will_give_unsatisfiable_if_all_rejected(self):
            @given(specifier, settings=settings)
            def nope(x):
                assume(False)
            with self.assertRaises(Unsatisfiable):
                nope()

        def test_will_find_a_constant_failure(self):
            @given(specifier, settings=settings)
            def nope(x):
                raise Rejected()
            with self.assertRaises(Rejected):
                nope()

        @specifier_test
        def test_is_basic(self, value, rnd):
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
        def test_only_raises_bad_data_in_from_basic(self, value, rnd):
            basic = strat.to_basic(value)

            messed_basic = mess_with_basic_data(basic, rnd)
            try:
                strat.from_basic(messed_basic)
            except BadData:
                pass

        @specifier_test
        def test_can_round_trip_through_the_database(self, template, rnd):
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
        def test_template_is_hashable(self, template, rnd):
            hash(template)
            # It can be easy to forget to convert a list...
            hash(strat.from_basic(strat.to_basic(template)))

        @specifier_test
        def test_can_minimize_to_empty(self, template, rnd):
            simplest = list(strat.simplify_such_that(
                rnd,
                template, lambda x: True
            ))[-1]
            assert list(strat.full_simplify(rnd, simplest)) == []

        @specifier_test
        def test_can_complete_falsify_loop(self, template, rnd):
            for _ in strat.full_simplify(rnd, template):
                pass

        @given(Random, settings=Settings(max_examples=1000))
        def test_can_create_templates(self, random):
            parameter = strat.draw_parameter(random)
            strat.draw_template(BuildContext(random), parameter)

    return ValidationSuite
