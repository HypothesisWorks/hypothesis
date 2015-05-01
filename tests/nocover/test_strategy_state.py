# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import math
import hashlib
from copy import deepcopy
from random import Random
from decimal import Decimal
from fractions import Fraction

from hypothesis import Settings, Verbosity, find, given, assume, strategy
from hypothesis.errors import NoExamples
from hypothesis.database import ExampleDatabase
from hypothesis.stateful import Bundle, RuleBasedStateMachine, \
    StateMachineSearchStrategy, rule
from hypothesis.specifiers import just, streaming, sampled_from, \
    floats_in_range, integers_in_range
from hypothesis.utils.show import show
from hypothesis.strategytests import TemplatesFor
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.searchstrategy.strategies import BuildContext

small_settings = Settings(average_list_length=2)


class HypothesisSpec(RuleBasedStateMachine):

    def __init__(self):
        super(HypothesisSpec, self).__init__()
        self.database = None

    strategies = Bundle('strategy')
    tuples = Bundle('tuples')
    objects = Bundle('objects')
    streaming_strategies = Bundle('streams')

    strats_with_parameters = Bundle('strats_with_parameters')
    strats_with_templates = Bundle('strats_with_templates')

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

    @rule(st=strats_with_templates)
    def reify(self, st):
        strat, temp = st
        strat.reify(temp)

    @rule(target=strats_with_templates, st=strats_with_templates)
    def via_basic(self, st):
        strat, temp = st
        temp = strat.from_basic(strat.to_basic(temp))
        return (strat, temp)

    @rule(targets=(strategies, streaming_strategies), strat=strategies)
    def build_stream(self, strat):
        return strategy(streaming(strat))

    @rule(stream_strat=streaming_strategies, index=integers_in_range(0, 500))
    def eval_stream(self, stream_strat, index):
        stream = stream_strat.example()
        list(stream[:index])

    @rule(target=strats_with_templates, st=strats_with_templates, r=Random)
    def simplify(self, st, r):
        strat, temp = st
        for temp in strat.full_simplify(r, temp):
            break
        return (strat, temp)

    @rule(strat=strategies, r=Random)
    def find_constant_failure(self, strat, r):
        with Settings(
            verbosity=Verbosity.quiet, max_examples=1,
            min_satisfying_examples=0,
            database=self.database,
        ):
            @given(strat, random=r,)
            def test(x):
                assert False

            try:
                test()
            except AssertionError:
                pass

    @rule(strat=strategies, r=Random, mex=integers_in_range(1, 500))
    def find_weird_failure(self, strat, r, mex):
        with Settings(
            verbosity=Verbosity.quiet, max_examples=mex,
            min_satisfying_examples=0,
            database=self.database,
        ):
            @given(strat, random=r,)
            def test(x):
                assert Random(
                    hashlib.md5(show(x).encode('utf-8')).digest()
                ).randint(0, 5)

            try:
                test()
            except AssertionError:
                pass

    @rule(target=strats_with_parameters, strat=strategies, r=Random)
    def draw_parameter(self, strat, r):
        return (strat, strat.draw_parameter(r))

    @rule(target=strats_with_templates, sp=strats_with_parameters, r=Random)
    def draw_template(self, sp, r):
        strat, param = sp
        return (strat, strat.draw_template(BuildContext(r), param))

    @rule(st=strats_with_templates)
    def check_serialization(self, st):
        strat, template = st
        as_basic = strat.to_basic(template)
        assert show(strat.reify(template)) == show(strat.reify(
            strat.from_basic(as_basic)))
        assert as_basic == strat.to_basic(strat.from_basic(as_basic))

    @rule(target=strategies, spec=sampled_from((
        int, bool, float, complex, Fraction, Decimal,
        text_type, binary_type, None, StateMachineSearchStrategy(),
        (),
    )))
    @rule(target=strategies, spec=tuples)
    def strategy(self, spec):
        return strategy(spec, settings=small_settings)

    @rule(
        target=strategies,
        source=strategies,
        level=integers_in_range(1, 10),
        mixer=text_type)
    def filtered_strategy(s, source, level, mixer):
        def is_good(x):
            return bool(Random(
                hashlib.md5((mixer + show(x)).encode('utf-8')).digest()
            ).randint(0, level))
        return source.filter(is_good)

    @rule(target=strategies, elements=strategies)
    def list_strategy(self, elements):
        return strategy([elements], settings=small_settings)

    @rule(target=strategies, l=strategies, r=strategies)
    def or_strategy(self, l, r):
        return l | r

    @rule(
        target=strategies,
        source=strategies, result=strategies, mixer=text_type)
    def mapped_strategy(self, source, result, mixer):
        cache = {}

        def do_map(value):
            rep = show(value)
            try:
                return deepcopy(cache[rep])
            except KeyError:
                pass
            random = Random(
                hashlib.md5((mixer + rep).encode('utf-8')).digest()
            )
            outcome_template = result.draw_and_produce_from_random(random)
            cache[rep] = result.reify(outcome_template)
            return deepcopy(cache[rep])
        return source.map(do_map)

    @rule(
        target=strategies,
        left=float, right=float
    )
    def float_range(self, left, right):
        for f in (math.isnan, math.isinf):
            for x in (left, right):
                assume(not f(x))
        left, right = sorted((left, right))
        return strategy(floats_in_range(left, right))

    @rule(
        target=strategies,
        source=strategies, result1=strategies, result2=strategies,
        mixer=text_type, p=floats_in_range(0, 1))
    def flatmapped_strategy(self, source, result1, result2, mixer, p):
        assume(result1 is not result2)

        def do_map(value):
            rep = show(value)
            random = Random(
                hashlib.md5((mixer + rep).encode('utf-8')).digest()
            )
            if random.random() <= p:
                return result1
            else:
                return result2
        return source.flatmap(do_map)

    @rule(strat=strategies)
    def is_size_consistent(self, strat):
        assert strat.size_lower_bound == strat.size_upper_bound

    @rule(target=strategies, value=objects)
    def just_strategy(self, value):
        return strategy(just(value))

    @rule(target=tuples, source=strategies)
    def single_tuple(self, source):
        return (source,)

    @rule(target=tuples, l=tuples, r=tuples)
    def cat_tuples(self, l, r):
        return l + r

    @rule(target=objects, strat=strategies)
    def get_example(self, strat):
        try:
            strat.example()
        except NoExamples:
            # Because of filtering some strategies we look for don't actually
            # have any examples.
            pass

    @rule(target=strategies, left=int, right=int)
    def integer_range(self, left, right):
        left, right = sorted((left, right))
        return strategy(integers_in_range(left, right))

    @rule(strat=strategies)
    def repr_is_good(self, strat):
        assert ' at 0x' not in repr(strat)

    @rule(strat=strategies)
    def can_find_as_many_templates_as_size(self, strat):
        tempstrat = strategy(TemplatesFor(strat))
        n = min(10, strat.size_lower_bound)
        found = []
        with Settings(verbosity=Verbosity.quiet, timeout=2.0):
            for _ in range(n):
                x = find(
                    tempstrat, lambda t: t not in found,
                )
                found.append(x)

    @rule(strat=strategies)
    def can_simultaneously_simplify(self, strat):
        if strat.size_upper_bound < 2:
            return
        lists = strategy([strat])
        simul = find(
            lists,
            lambda x: (
                20 <= len(x) <= 30 and
                len(set(map(show, x))) >= 2
            ), settings=Settings(verbosity=Verbosity.quiet, timeout=2.0))
        assert len(simul) == 20
        assert len(set(map(show, simul))) == 2


TestHypothesis = HypothesisSpec.TestCase

TestHypothesis.settings.stateful_step_count = 30
TestHypothesis.settings.max_shrinks = 500
TestHypothesis.settings.timeout = 60
TestHypothesis.settings.min_satisfying_examples = 1
