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

"""Support for testing your custom implementations of specifiers."""


from __future__ import division, print_function, absolute_import

import hashlib
from random import Random
from unittest import TestCase
from itertools import islice
from collections import namedtuple

from hypothesis import given, assume
from hypothesis.errors import BadData, Unsatisfiable, BadTemplateDraw
from hypothesis.control import BuildContext
from hypothesis.database import ExampleDatabase
from hypothesis.settings import Settings
from hypothesis.strategies import lists, randoms, integers
from hypothesis.internal.compat import hrange, text_type, integer_types
from hypothesis.utils.extmethod import ExtMethod
from hypothesis.database.backend import SQLiteBackend
from hypothesis.internal.tracker import Tracker
from hypothesis.searchstrategy.strategies import strategy, SearchStrategy

TemplatesFor = namedtuple(u'TemplatesFor', (u'base',))


class TemplatesStrategy(SearchStrategy):

    def __init__(self, base_strategy):
        super(TemplatesStrategy, self).__init__()
        self.base_strategy = base_strategy
        self.template_upper_bound = base_strategy.template_upper_bound

    def __repr__(self):
        return u'templates_for(%r)' % (self.base_strategy,)

    def draw_parameter(self, random):
        return self.base_strategy.draw_parameter(random)

    def strictly_simpler(self, x, y):
        return self.base_strategy.strictly_simpler(x, y)

    def draw_template(self, random, pv):
        return self.base_strategy.draw_template(random, pv)

    def reify(self, template):
        return template

    def to_basic(self, template):
        return self.base_strategy.to_basic(template)

    def from_basic(self, data):
        return self.base_strategy.from_basic(data)

    def simplifiers(self, random, template):
        return self.base_strategy.simplifiers(random, template)


@strategy.extend(TemplatesFor)
def templates_for_strategy(specifier, settings):
    return TemplatesStrategy(strategy(specifier.base, settings))


def templates_for(strat):
    return TemplatesStrategy(strategy(strat))


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
        return text.encode(u'utf-8')
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
        return float(u'nan')


def strategy_test_suite(
    specifier,
    max_examples=20, random=None,
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
        templates_for(specifier), randoms(), settings=settings
    )

    class ValidationSuite(TestCase):

        def __repr__(self):
            return u'strategy_test_suite(%s)' % (
                repr(specifier),
            )

        @given(specifier, settings=settings)
        def test_does_not_error(self, value):
            pass

        def test_can_give_example(self):
            strat.example()

        def test_can_give_list_of_examples(self):
            strategy(lists(strat)).example()

        def test_will_give_unsatisfiable_if_all_rejected(self):
            @given(specifier, settings=settings)
            def nope(x):
                assume(False)
            self.assertRaises(Unsatisfiable, nope)

        def test_will_find_a_constant_failure(self):
            @given(specifier, settings=settings)
            def nope(x):
                raise Rejected()
            self.assertRaises(Rejected, nope)

        def test_will_find_a_failure_from_the_database(self):
            db = ExampleDatabase()

            @given(specifier, settings=Settings(max_examples=10, database=db))
            def nope(x):
                raise Rejected()
            try:
                for i in hrange(3):
                    self.assertRaises(Rejected, nope)  # pragma: no cover
            finally:
                db.close()

        @given(
            templates_for(specifier), templates_for(specifier),
            settings=settings
        )
        def test_simplicity_is_asymmetric(self, x, y):
            assert not (
                strat.strictly_simpler(x, y) and
                strat.strictly_simpler(y, x)
            )

        @given(integers(), settings=settings)
        def test_templates_generated_from_same_random_are_equal(self, i):
            try:
                t1 = strat.draw_and_produce(Random(i))
                t2 = strat.draw_and_produce(Random(i))
            except BadTemplateDraw:
                assume(False)

            if t1 is not t2:
                assert t1 == t2
                assert hash(t1) == hash(t2)

        @given(integers(), settings=settings)
        def test_templates_generated_from_same_random_are_equal_after_reify(
            self, i
        ):
            try:
                t1 = strat.draw_and_produce(Random(i))
                t2 = strat.draw_and_produce(Random(i))
            except BadTemplateDraw:
                assume(False)
            if t1 is not t2:
                with BuildContext():
                    strat.reify(t1)
                with BuildContext():
                    strat.reify(t2)
                assert t1 == t2
                assert hash(t1) == hash(t2)

        @given(randoms(), settings=settings)
        def test_will_handle_a_really_weird_failure(self, rnd):
            db = ExampleDatabase()

            @given(
                specifier,
                settings=Settings(
                    database=db,
                    max_examples=max_examples,
                    min_satisfying_examples=2,
                    average_list_length=2.0,
                ), random=rnd
            )
            def nope(x):
                s = hashlib.sha1(repr(x).encode(u'utf-8')).digest()
                assert Random(s).randint(0, 1) == Random(s).randint(0, 1)
                if Random(s).randint(0, 1):
                    raise Rejected(u'%r with digest %r' % (
                        x, s
                    ))
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
                backend=SQLiteBackend(u':memory:'),
            )
            try:
                storage = empty_db.storage(u'round trip')
                storage.save(template, strat)
                values = list(storage.fetch(strat))
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
            simplest = template
            tracker = Tracker()
            while True:
                for t in strat.full_simplify(rnd, simplest):
                    if tracker.track(t) == 1:
                        simplest = t
                        break
                else:
                    break
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

        @given(randoms(), settings=Settings(max_examples=1000))
        def test_can_create_templates(self, random):
            parameter = strat.draw_parameter(random)
            try:
                strat.draw_template(random, parameter)
            except BadTemplateDraw:
                assume(False)

    return ValidationSuite
