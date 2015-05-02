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

import hashlib
from random import Random
from unittest import TestCase
from itertools import islice
from collections import namedtuple

from hypothesis import given, assume
from hypothesis.errors import BadData, Unsatisfiable
from hypothesis.database import ExampleDatabase
from hypothesis.settings import Settings
from hypothesis.utils.show import show
from hypothesis.internal.compat import hrange, text_type, integer_types
from hypothesis.utils.extmethod import ExtMethod
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

    def strictly_simpler(self, x, y):
        return self.base_strategy.strictly_simpler(x, y)

    def produce_template(self, context, pv):
        return self.base_strategy.produce_template(context, pv)

    def reify(self, template):
        return template

    def to_basic(self, template):
        return self.base_strategy.to_basic(template)

    def from_basic(self, data):
        return self.base_strategy.from_basic(data)

    def simplifiers(self, random, template):
        return self.base_strategy.simplifiers(random, template)


@strategy.extend(TemplatesFor)
def templates_for(specifier, settings):
    return TemplatesStrategy(strategy(specifier.base, settings))


class Rejected(Exception):
    pass


mess_with_basic_data = ExtMethod()


def mutate_basic(basic, random):
    if not random.randint(0, 2):
        if isinstance(basic, text_type):
            return list(basic)
        elif isinstance(basic, integer_types):
            try:
                return float(basic)
            except OverflowError:
                return -basic
        else:
            return text_type(repr(basic))
    return mess_with_basic_data(basic, random)


@mess_with_basic_data.extend(object)
def test_mess_with_anything(o, random):
    return o


def mess_with_int(i, random):  # pragma: no cover
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


@mess_with_basic_data.extend(text_type)
def mess_with_text(text, random):  # pragma: no cover
    if random.randint(0, 1):
        return text.encode('utf-8')
    else:
        return text


@mess_with_basic_data.extend(list)
def mess_with_list(ls, random):  # pragma: no cover
    ls = list(ls)
    if not ls:
        if random.randint(0, 1):
            ls.append(random.randint(-2 ** 128, 2 ** 128))
        return ls
    i = random.randint(0, len(ls))
    if i < len(ls):
        ls[i] = mutate_basic(ls[i], random)
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
    max_examples=100, random=None,
):
    settings = Settings(
        database=None,
        max_examples=max_examples,
        min_satisfying_examples=2,
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

        def test_will_find_a_failure_from_the_database(self):
            db = ExampleDatabase()

            @given(specifier, settings=Settings(max_examples=10, database=db))
            def nope(x):
                raise Rejected()
            try:
                for i in hrange(3):
                    with self.assertRaises(Rejected):
                        nope()  # pragma: no branch
            finally:
                db.close()

        @given(
            TemplatesFor(specifier), TemplatesFor(specifier),
            settings=settings
        )
        def test_simplicity_is_asymmetric(self, x, y):
            assert not (
                strat.strictly_simpler(x, y) and
                strat.strictly_simpler(y, x)
            )

        def test_will_handle_a_really_weird_failure(self):
            db = ExampleDatabase()

            @given(
                specifier,
                settings=Settings(
                    database=db,
                    max_examples=max_examples,
                    min_satisfying_examples=2,
                    average_list_length=2.0,
                )
            )
            def nope(x):
                s = hashlib.sha1(show(x).encode('utf-8')).digest()
                if Random(s).randint(0, 1):
                    raise Rejected()
            try:
                try:
                    nope()
                except Rejected:
                    pass
                try:
                    nope()
                except Rejected:
                    pass
            finally:
                db.close()

        @specifier_test
        def test_is_basic(self, value, rnd):
            def is_basic(v):
                if v is None or isinstance(v, text_type):
                    return True
                if isinstance(v, integer_types):
                    return not (abs(v) >> 64)
                if isinstance(v, list):
                    return all(is_basic(w) for w in v)
                return False
            supposedly_basic = strat.to_basic(value)
            self.assertTrue(is_basic(supposedly_basic), repr(supposedly_basic))

        @specifier_test
        def test_only_raises_bad_data_in_from_basic(self, value, rnd):
            basic = strat.to_basic(value)

            messed_basic = mutate_basic(basic, rnd)
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

        @given(
            TemplatesFor(specifier), Random,
            [[int]],
            settings=settings
        )
        def test_apply_all_simplifiers(self, template, rnd, path):
            path = list(filter(None, path))
            assume(path)
            current_template = template
            for local_route in path:
                simplifiers = list(strat.simplifiers(random, current_template))
                if not simplifiers:
                    break
                for i in local_route:
                    simplify = simplifiers[abs(i) % len(simplifiers)]
                    simpler = list(simplify(
                        rnd, current_template
                    ))
                    if simpler:
                        current_template = random.choice(simpler)

        @specifier_test
        def test_can_minimize_to_empty(self, template, rnd):
            simplest = template
            try:
                while True:
                    simplest = next(strat.full_simplify(rnd, simplest))
            except StopIteration:
                pass
            assert list(strat.full_simplify(rnd, simplest)) == []

        @specifier_test
        def test_full_simplify_completes(self, template, rnd):
            # Cut off at 1000 for the occasional case where we get
            # really very large templates which have too many simplifies.
            for x in islice(strat.full_simplify(rnd, template), 1000):
                pass

        @specifier_test
        def test_does_not_increase_complexity(self, template, rnd):
            for s in islice(strat.full_simplify(rnd, template), 100):
                assert not strat.strictly_simpler(template, s)

        @given(Random, settings=Settings(max_examples=1000))
        def test_can_create_templates(self, random):
            parameter = strat.draw_parameter(random)
            strat.draw_template(BuildContext(random), parameter)

    return ValidationSuite
