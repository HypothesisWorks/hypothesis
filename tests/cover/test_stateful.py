# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import inspect
from random import Random
from collections import namedtuple

import pytest
from hypothesis import Settings, assume, strategy
from hypothesis.errors import Flaky, BadData, InvalidDefinition
from tests.common.utils import capture_out
from hypothesis.stateful import Bundle, GenericStateMachine, \
    RuleBasedStateMachine, StateMachineSearchStrategy, rule
from hypothesis.specifiers import just, sampled_from, integers_in_range


class SetStateMachine(GenericStateMachine):

    def __init__(self):
        self.elements = []

    def steps(self):
        strat = strategy((just(False), int))
        if self.elements:
            strat |= strategy((just(True), sampled_from(self.elements)))
        return strat

    def execute_step(self, step):
        delete, value = step
        if delete:
            self.elements.remove(value)
            assert value not in self.elements
        else:
            self.elements.append(value)


class OrderedStateMachine(GenericStateMachine):

    def __init__(self):
        self.counter = 0

    def steps(self):
        return strategy(
            integers_in_range(self.counter - 1, self.counter + 50)
        )

    def execute_step(self, step):
        assert step >= self.counter
        self.counter = step


class GoodSet(GenericStateMachine):

    def __init__(self):
        self.stuff = set()

    def steps(self):
        return strategy((bool, int))

    def execute_step(self, step):
        delete, value = step
        if delete:
            self.stuff.discard(value)
        else:
            self.stuff.add(value)
        assert delete == (value not in self.stuff)


class UnreliableStrategyState(GenericStateMachine):
    n = 8

    def __init__(self):
        self.random = Random()
        self.counter = 0

    def steps(self):
        if self.random.randint(0, 1):
            return strategy([bool])
        else:
            return strategy(int)

    def execute_step(self, step):
        self.counter += 1
        assert self.counter < self.n


Leaf = namedtuple('Leaf', ('label',))
Split = namedtuple('Split', ('left', 'right'))


class BalancedTrees(RuleBasedStateMachine):
    trees = 'BinaryTree'

    @rule(target=trees, x=bool)
    def leaf(self, x):
        return Leaf(x)

    @rule(target=trees, left=Bundle(trees), right=Bundle(trees))
    def split(self, left, right):
        return Split(left, right)

    @rule(tree=Bundle(trees))
    def test_is_balanced(self, tree):
        if isinstance(tree, Leaf):
            return
        else:
            assert abs(self.size(tree.left) - self.size(tree.right)) <= 1
            self.test_is_balanced(tree.left)
            self.test_is_balanced(tree.right)

    def size(self, tree):
        if isinstance(tree, Leaf):
            return 1
        else:
            return 1 + self.size(tree.left) + self.size(tree.right)


class DepthCharge(object):

    def __init__(self, value):
        if value is None:
            self.depth = 0
        else:
            self.depth = value.depth + 1


class DepthMachine(RuleBasedStateMachine):
    charges = Bundle('charges')

    @rule(targets=(charges,), child=charges)
    @rule(targets=(charges,), child=None)
    def charge(self, child):
        return DepthCharge(child)

    @rule(check=charges)
    def is_not_too_deep(self, check):
        assert check.depth < 3

bad_machines = (
    OrderedStateMachine, SetStateMachine, BalancedTrees,
    UnreliableStrategyState, DepthMachine,
)


cheap_bad_machines = list(bad_machines)
cheap_bad_machines.remove(BalancedTrees)
cheap_bad_machines.remove(UnreliableStrategyState)


with_cheap_bad_machines = pytest.mark.parametrize(
    'machine',
    cheap_bad_machines, ids=[t.__name__ for t in cheap_bad_machines]
)


@with_cheap_bad_machines
def test_can_serialize_statemachine_execution(machine):
    runner = machine.find_breaking_runner()
    strategy = StateMachineSearchStrategy()
    new_runner = strategy.from_basic(strategy.to_basic(runner))
    with pytest.raises(AssertionError):
        new_runner.run(machine())
    r = Random(1)

    for simplifier in strategy.simplifiers(r, new_runner):
        try:
            next(simplifier(r, new_runner))
        except StopIteration:
            pass


@with_cheap_bad_machines
def test_can_shrink_deserialized_execution_without_running(machine):
    runner = machine.find_breaking_runner()
    strategy = StateMachineSearchStrategy()
    new_runner = strategy.from_basic(strategy.to_basic(runner))
    r = Random(1)

    for simplifier in strategy.simplifiers(r, new_runner):
        try:
            next(simplifier(r, new_runner))
        except StopIteration:
            pass


def test_rejects_invalid_step_sizes_in_data():
    runner = DepthMachine.find_breaking_runner()
    strategy = StateMachineSearchStrategy()
    basic = strategy.to_basic(runner)
    assert isinstance(basic[2], int)
    basic[2] = -1
    with pytest.raises(BadData):
        strategy.from_basic(basic)
    basic[2] = 1000000
    with pytest.raises(BadData):
        strategy.from_basic(basic)


@with_cheap_bad_machines
def test_can_full_simplify_breaking_example(machine):
    runner = machine.find_breaking_runner()
    strategy = StateMachineSearchStrategy()
    r = Random(1)
    for _ in strategy.full_simplify(r, runner):
        pass


def test_can_truncate_template_record():
    class Breakable(GenericStateMachine):
        counter_start = 0

        def __init__(self):
            self.counter = type(self).counter_start

        def steps(self):
            return strategy(int)

        def execute_step(self, step):
            self.counter += 1
            if self.counter > 10:
                assert step < 0

    runner = Breakable.find_breaking_runner()
    strat = StateMachineSearchStrategy()
    r = Random(1)
    simplifiers = list(strat.simplifiers(r, runner))
    assert simplifiers
    assert any('convert_simplifier' in s.__name__ for s in simplifiers)
    while runner.record:
        runner.record.pop()

    assert not runner.record
    for s in simplifiers:
        for t in s(r, runner):
            pass


@pytest.mark.parametrize(
    'machine',
    bad_machines, ids=[t.__name__ for t in bad_machines]
)
def test_bad_machines_fail(machine):
    test_class = machine.TestCase
    try:
        with capture_out() as o:
            with pytest.raises(AssertionError):
                test_class().runTest()
    except Exception:
        print(o.getvalue())
        raise
    v = o.getvalue()
    print(v)
    assert 'Step #1' in v
    assert 'Step #50' not in v


class GivenLikeStateMachine(GenericStateMachine):

    def steps(self):
        return strategy([bool])

    def execute_step(self, step):
        assume(any(step))


def test_can_get_test_case_off_machine_instance():
    assert GoodSet().TestCase is GoodSet().TestCase
    assert GoodSet().TestCase is not None


class FlakyStateMachine(RuleBasedStateMachine):

    @rule()
    def boom(self):
        assert not any(
            t[3] == 'find_breaking_runner'
            for t in inspect.getouterframes(inspect.currentframe())
        )


def test_flaky_raises_flaky():
    with pytest.raises(Flaky):
        FlakyStateMachine.TestCase().runTest()


def test_empty_machine_is_invalid():
    class EmptyMachine(RuleBasedStateMachine):
        pass

    with pytest.raises(InvalidDefinition):
        EmptyMachine.TestCase().runTest()


def test_machine_with_no_terminals_is_invalid():
    class NonTerminalMachine(RuleBasedStateMachine):

        @rule(value=Bundle('hi'))
        def bye(self, hi):
            pass

    with pytest.raises(InvalidDefinition):
        NonTerminalMachine.TestCase().runTest()


class DynamicMachine(RuleBasedStateMachine):

    @rule(value=Bundle('hi'))
    def test_stuff(x):
        pass

DynamicMachine.define_rule(
    targets=(), function=lambda self: 1, arguments={}
)


class IntAdder(RuleBasedStateMachine):
    pass

IntAdder.define_rule(
    targets=('ints',), function=lambda self, x: x, arguments={
        'x': int
    }
)

IntAdder.define_rule(
    targets=('ints',), function=lambda self, x, y: x, arguments={
        'x': int, 'y': Bundle('ints'),
    }
)

with Settings(max_examples=10):
    TestGoodSets = GoodSet.TestCase
    TestGivenLike = GivenLikeStateMachine.TestCase
    TestDynamicMachine = DynamicMachine.TestCase
    TestIntAdder = IntAdder.TestCase


def test_picks_up_settings_at_first_use_of_testcase():
    assert TestDynamicMachine.settings.max_examples == 10


def test_new_rules_are_picked_up_before_and_after_rules_call():
    class Foo(RuleBasedStateMachine):
        pass
    Foo.define_rule(
        targets=(), function=lambda self: 1, arguments={}
    )
    assert len(Foo.rules()) == 1
    Foo.define_rule(
        targets=(), function=lambda self: 2, arguments={}
    )
    assert len(Foo.rules()) == 2


def test_settings_are_independent():
    s = Settings()
    orig = s.max_examples
    with s:
        class Foo(RuleBasedStateMachine):
            pass
        Foo.define_rule(
            targets=(), function=lambda self: 1, arguments={}
        )
        Foo.TestCase.settings.max_examples = 1000000
    assert s.max_examples == orig


def test_minimizes_errors_in_teardown():
    class Foo(GenericStateMachine):

        def __init__(self):
            self.counter = 0

        def steps(self):
            return strategy(())

        def execute_step(self, value):
            self.counter += 1

        def teardown(self):
            assert not self.counter

    runner = Foo.find_breaking_runner()
    assert runner.n_steps == 1

    with pytest.raises(AssertionError):
        runner.run(Foo(), print_steps=True)


def test_can_produce_minimal_outcomes_from_unreliable_strategies():
    runner = UnreliableStrategyState.find_breaking_runner()
    n = UnreliableStrategyState.n

    assert runner.n_steps == n
    assert len(runner.record) >= n
    for strat, data in runner.record[:n]:
        template = strat.from_basic(data[-1])
        value = strat.reify(template)
        assert value in ([], 0)
