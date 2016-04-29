# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

"""Support for testing your custom implementations of specifiers."""

from __future__ import division, print_function, absolute_import

import hashlib
from random import Random
from unittest import TestCase

from hypothesis import settings as Settings
from hypothesis import seed, given, reject
from hypothesis.errors import Unsatisfiable
from hypothesis.database import ExampleDatabase
from hypothesis.strategies import lists, integers
from hypothesis.internal.compat import hrange


class Rejected(Exception):
    pass


def strategy_test_suite(
    specifier,
    max_examples=10, random=None,
):
    settings = Settings(
        database=None,
        max_examples=max_examples,
        max_iterations=max_examples * 2,
        min_satisfying_examples=2,
    )
    random = random or Random()
    strat = specifier

    class ValidationSuite(TestCase):

        def __repr__(self):
            return 'strategy_test_suite(%s)' % (
                repr(specifier),
            )

        @given(specifier)
        @settings
        def test_does_not_error(self, value):
            pass

        if strat.supports_find:
            def test_can_give_example(self):
                strat.example()

            def test_can_give_list_of_examples(self):
                lists(strat).example()

        def test_will_give_unsatisfiable_if_all_rejected(self):
            @given(specifier)
            @settings
            def nope(x):
                reject()
            self.assertRaises(Unsatisfiable, nope)

        def test_will_find_a_constant_failure(self):
            @given(specifier)
            @settings
            def nope(x):
                raise Rejected()
            self.assertRaises(Rejected, nope)

        def test_will_find_a_failure_from_the_database(self):
            db = ExampleDatabase()

            @given(specifier)
            @Settings(settings, max_examples=10, database=db)
            def nope(x):
                raise Rejected()
            try:
                for i in hrange(3):
                    self.assertRaises(Rejected, nope)  # pragma: no cover
            finally:
                db.close()

        @given(integers())
        @settings
        def test_will_handle_a_really_weird_failure(self, s):
            db = ExampleDatabase()

            @given(specifier)
            @Settings(
                settings,
                database=db,
                max_examples=max_examples,
                min_satisfying_examples=2,
            )
            @seed(s)
            def nope(x):
                s = hashlib.sha1(repr(x).encode('utf-8')).digest()
                assert Random(s).randint(0, 1) == Random(s).randint(0, 1)
                if Random(s).randint(0, 1):
                    raise Rejected('%r with digest %r' % (
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

    return ValidationSuite
