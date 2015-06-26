# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

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

from hypothesis import Settings, Verbosity, find, given, assume, strategy
from hypothesis.errors import BadData, NoExamples
from hypothesis.database import ExampleDatabase
from hypothesis.stateful import Bundle, RuleBasedStateMachine, \
    StateMachineSearchStrategy, rule
from hypothesis.strategies import just, none, text, lists, binary, \
    floats, tuples, randoms, booleans, decimals, integers, fractions, \
    streaming, sampled_from, complex_numbers
from hypothesis.utils.show import show
from hypothesis.utils.size import clamp
from hypothesis.strategytests import mutate_basic, templates_for
from hypothesis.internal.compat import PY3, PYPY
from hypothesis.searchstrategy.numbers import float_to_int, int_to_float

AVERAGE_LIST_LENGTH = 2


class HypothesisSpec(RuleBasedStateMachine):

    def __init__(self):
        super(HypothesisSpec, self).__init__()
        self.database = None

    strategies = Bundle('strategy')
    strategy_tuples = Bundle('tuples')
    objects = Bundle('objects')
    streaming_strategies = Bundle('streams')
    basic_data = Bundle('basic')
    varied_floats = Bundle('varied_floats')

    strats_with_parameters = Bundle('strats_with_parameters')
    strats_with_templates = Bundle('strats_with_templates')
    strats_with_2_templates = Bundle('strats_with_2_templates')

    def teardown(self):
        self.clear_database()

    @rule(target=basic_data, st=strats_with_templates)
    def to_basic(self, st):
        return st[0].to_basic(st[1])

    @rule(data=basic_data, strat=strategies)
    def from_basic(self, data, strat):
        try:
            template = strat.from_basic(data)
        except BadData:
            return
        strat.reify(template)

    @rule(target=basic_data, data=basic_data, r=randoms())
    def mess_with_basic(self, data, r):
        return mutate_basic(data, r)

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

    @rule(
        targets=(strategies, streaming_strategies),
        strat=strategies, i=integers(1, 10))
    def evalled_stream(self, strat, i):
        return strategy(streaming(strat)).map(lambda x: list(x[:i]) and x)

    @rule(stream_strat=streaming_strategies, index=integers(0, 50))
    def eval_stream(self, stream_strat, index):
        try:
            stream = stream_strat.example()
            list(stream[:index])
        except NoExamples:
            pass

    @rule(target=strats_with_templates, st=strats_with_templates, r=randoms())
    def simplify(self, st, r):
        strat, temp = st
        for temp in strat.full_simplify(r, temp):
            break
        return (strat, temp)

    @rule(strat=strategies, r=randoms(), mshr=integers(0, 100))
    def find_constant_failure(self, strat, r, mshr):
        with Settings(
            verbosity=Verbosity.quiet, max_examples=1,
            min_satisfying_examples=0,
            database=self.database,
            max_shrinks=mshr,
        ):
            @given(strat, random=r,)
            def test(x):
                assert False

            try:
                test()
            except AssertionError:
                pass

    @rule(
        strat=strategies, r=randoms(), p=floats(0, 1),
        mex=integers(1, 10), mshr=integers(1, 100)
    )
    def find_weird_failure(self, strat, r, mex, p, mshr):
        with Settings(
            verbosity=Verbosity.quiet, max_examples=mex,
            min_satisfying_examples=0,
            database=self.database,
            max_shrinks=mshr,
        ):
            @given(strat, random=r,)
            def test(x):
                assert Random(
                    hashlib.md5(show(x).encode('utf-8')).digest()
                ).random() <= p

            try:
                test()
            except AssertionError:
                pass

    @rule(target=strats_with_parameters, strat=strategies, r=randoms())
    def draw_parameter(self, strat, r):
        return (strat, strat.draw_parameter(r))

    @rule(target=strats_with_templates, sp=strats_with_parameters, r=randoms())
    def draw_template(self, sp, r):
        strat, param = sp
        return (strat, strat.draw_template(r, param))

    @rule(
        target=strats_with_2_templates,
        sp=strats_with_parameters, r=randoms())
    def draw_templates(self, sp, r):
        strat, param = sp
        return (
            strat,
            strat.draw_template(r, param),
            strat.draw_template(r, param),
        )

    @rule(st=strats_with_templates)
    def check_serialization(self, st):
        strat, template = st
        as_basic = strat.to_basic(template)
        assert show(strat.reify(template)) == show(strat.reify(
            strat.from_basic(as_basic)))
        assert as_basic == strat.to_basic(strat.from_basic(as_basic))

    @rule(target=strategies, spec=sampled_from((
        integers(), booleans(), floats(), complex_numbers(),
        fractions(), decimals(), text(), binary(), none(),
        StateMachineSearchStrategy(), tuples(),
    )))
    def strategy(self, spec):
        return spec

    @rule(target=strategies, spec=strategy_tuples)
    def strategy_for_tupes(self, spec):
        return tuples(*spec)

    @rule(
        target=strategies,
        source=strategies,
        level=integers(1, 10),
        mixer=text())
    def filtered_strategy(s, source, level, mixer):
        def is_good(x):
            return bool(Random(
                hashlib.md5((mixer + show(x)).encode('utf-8')).digest()
            ).randint(0, level))
        return source.filter(is_good)

    @rule(target=strategies, elements=strategies)
    def list_strategy(self, elements):
        return lists(elements, average_size=AVERAGE_LIST_LENGTH)

    @rule(target=strategies, l=strategies, r=strategies)
    def or_strategy(self, l, r):
        return l | r

    @rule(
        target=strategies,
        source=strategies, result=strategies, mixer=text())
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
            outcome_template = result.draw_and_produce(random)
            cache[rep] = result.reify(outcome_template)
            return deepcopy(cache[rep])
        return source.map(do_map)

    @rule(target=varied_floats, source=floats())
    def float(self, source):
        return source

    @rule(
        target=varied_floats,
        source=varied_floats, offset=integers(-100, 100))
    def adjust_float(self, source, offset):
        return int_to_float(clamp(
            0,
            float_to_int(source) + offset,
            2 ** 64 - 1
        ))

    @rule(
        target=strategies,
        left=varied_floats, right=varied_floats
    )
    def float_range(self, left, right):
        for f in (math.isnan, math.isinf):
            for x in (left, right):
                assume(not f(x))
        left, right = sorted((left, right))
        assert left <= right
        return strategy(floats(left, right))

    @rule(
        target=strategies,
        source=strategies, result1=strategies, result2=strategies,
        mixer=text(), p=floats(0, 1))
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

    @rule(target=strategies, value=objects)
    def just_strategy(self, value):
        return strategy(just(value))

    @rule(target=strategy_tuples, source=strategies)
    def single_tuple(self, source):
        return (source,)

    @rule(target=strategy_tuples, l=strategy_tuples, r=strategy_tuples)
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

    @rule(target=strategies, left=integers(), right=integers())
    def integer_range(self, left, right):
        left, right = sorted((left, right))
        return strategy(integers(left, right))

    @rule(strat=strategies)
    def repr_is_good(self, strat):
        assert ' at 0x' not in repr(strat)

    @rule(strat=strategies, r=randoms())
    def can_find_as_many_templates_as_size(self, strat, r):
        tempstrat = templates_for(strat)
        n = min(10, strat.template_upper_bound)
        found = []
        with Settings(verbosity=Verbosity.quiet, timeout=2.0):
            for i in range(n):
                try:
                    x = find(
                        tempstrat, lambda t: t not in found,
                        random=r,
                    )
                except:
                    print('Exception at %d/%d. template_upper_bound=%r' % (
                        i, n, strat.template_upper_bound
                    ))
                    raise
                found.append(x)

MAIN = __name__ == '__main__'

if MAIN or not (PYPY and PY3):
    # Currently experiencing plausible jit bugs bugs on pypy3
    TestHypothesis = HypothesisSpec.TestCase

    TestHypothesis.settings.stateful_step_count = 100
    TestHypothesis.settings.max_shrinks = 500
    TestHypothesis.settings.timeout = 60
    TestHypothesis.settings.min_satisfying_examples = 0
    TestHypothesis.settings.verbosity = max(
        TestHypothesis.settings.verbosity, Verbosity.verbose
    )

if MAIN:
    TestHypothesis.settings.timeout = 500
    TestHypothesis().runTest()
