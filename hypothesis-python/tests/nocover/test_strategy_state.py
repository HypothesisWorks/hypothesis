# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import hashlib
import math
from random import Random

from hypothesis import Verbosity, assume, settings
from hypothesis.database import ExampleDatabase
from hypothesis.internal.compat import PYPY
from hypothesis.internal.floats import float_to_int, int_to_float
from hypothesis.stateful import Bundle, RuleBasedStateMachine, rule
from hypothesis.strategies import (
    binary,
    booleans,
    complex_numbers,
    data,
    decimals,
    floats,
    fractions,
    integers,
    just,
    lists,
    none,
    sampled_from,
    text,
    tuples,
)

AVERAGE_LIST_LENGTH = 2


def clamp(lower, value, upper):
    """Given a value and optional lower/upper bounds, 'clamp' the value so that
    it satisfies lower <= value <= upper."""
    if (lower is not None) and (upper is not None) and (lower > upper):
        raise ValueError("Cannot clamp with lower > upper: %r > %r" % (lower, upper))
    if lower is not None:
        value = max(lower, value)
    if upper is not None:
        value = min(value, upper)
    return value


class HypothesisSpec(RuleBasedStateMachine):
    def __init__(self):
        super(HypothesisSpec, self).__init__()
        self.database = None

    strategies = Bundle(u"strategy")
    strategy_tuples = Bundle(u"tuples")
    objects = Bundle(u"objects")
    basic_data = Bundle(u"basic")
    varied_floats = Bundle(u"varied_floats")

    def teardown(self):
        self.clear_database()

    @rule()
    def clear_database(self):
        if self.database is not None:
            self.database.close()
            self.database = None

    @rule()
    def set_database(self):
        self.teardown()
        self.database = ExampleDatabase()

    @rule(
        target=strategies,
        spec=sampled_from(
            (
                integers(),
                booleans(),
                floats(),
                complex_numbers(),
                fractions(),
                decimals(),
                text(),
                binary(),
                none(),
                tuples(),
            )
        ),
    )
    def strategy(self, spec):
        return spec

    @rule(target=strategies, values=lists(integers() | text(), min_size=1))
    def sampled_from_strategy(self, values):
        return sampled_from(values)

    @rule(target=strategies, spec=strategy_tuples)
    def strategy_for_tupes(self, spec):
        return tuples(*spec)

    @rule(target=strategies, source=strategies, level=integers(1, 10), mixer=text())
    def filtered_strategy(s, source, level, mixer):
        def is_good(x):
            return bool(
                Random(
                    hashlib.md5((mixer + repr(x)).encode(u"utf-8")).digest()
                ).randint(0, level)
            )

        return source.filter(is_good)

    @rule(target=strategies, elements=strategies)
    def list_strategy(self, elements):
        return lists(elements)

    @rule(target=strategies, left=strategies, right=strategies)
    def or_strategy(self, left, right):
        return left | right

    @rule(target=varied_floats, source=floats())
    def float(self, source):
        return source

    @rule(target=varied_floats, source=varied_floats, offset=integers(-100, 100))
    def adjust_float(self, source, offset):
        return int_to_float(clamp(0, float_to_int(source) + offset, 2 ** 64 - 1))

    @rule(target=strategies, left=varied_floats, right=varied_floats)
    def float_range(self, left, right):
        for f in (math.isnan, math.isinf):
            for x in (left, right):
                assume(not f(x))
        left, right = sorted((left, right))
        assert left <= right
        return floats(left, right)

    @rule(
        target=strategies,
        source=strategies,
        result1=strategies,
        result2=strategies,
        mixer=text(),
        p=floats(0, 1),
    )
    def flatmapped_strategy(self, source, result1, result2, mixer, p):
        assume(result1 is not result2)

        def do_map(value):
            rep = repr(value)
            random = Random(hashlib.md5((mixer + rep).encode(u"utf-8")).digest())
            if random.random() <= p:
                return result1
            else:
                return result2

        return source.flatmap(do_map)

    @rule(target=strategies, value=objects)
    def just_strategy(self, value):
        return just(value)

    @rule(target=strategy_tuples, source=strategies)
    def single_tuple(self, source):
        return (source,)

    @rule(target=strategy_tuples, left=strategy_tuples, right=strategy_tuples)
    def cat_tuples(self, left, right):
        return left + right

    @rule(target=objects, strat=strategies, data=data())
    def get_example(self, strat, data):
        data.draw(strat)

    @rule(target=strategies, left=integers(), right=integers())
    def integer_range(self, left, right):
        left, right = sorted((left, right))
        return integers(left, right)

    @rule(strat=strategies)
    def repr_is_good(self, strat):
        assert u" at 0x" not in repr(strat)


MAIN = __name__ == u"__main__"

TestHypothesis = HypothesisSpec.TestCase

TestHypothesis.settings = settings(
    TestHypothesis.settings,
    stateful_step_count=10 if PYPY else 50,
    verbosity=max(TestHypothesis.settings.verbosity, Verbosity.verbose),
    max_examples=10000 if MAIN else 200,
)

if MAIN:
    TestHypothesis().runTest()
