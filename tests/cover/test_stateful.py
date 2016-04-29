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

from __future__ import division, print_function, absolute_import

import inspect
from collections import namedtuple

import pytest

from hypothesis import settings as Settings
from hypothesis import assume
from hypothesis.errors import Flaky, InvalidDefinition
from hypothesis.control import current_build_context
from tests.common.utils import raises, capture_out
from hypothesis.database import ExampleDatabase
from hypothesis.stateful import rule, Bundle, precondition, \
    GenericStateMachine, RuleBasedStateMachine, \
    run_state_machine_as_test
from hypothesis.strategies import just, none, lists, binary, tuples, \
    choices, booleans, integers, sampled_from
from hypothesis.internal.compat import print_unicode


class SetStateMachine(GenericStateMachine):

    def __init__(self):
        self.elements = []

    def steps(self):
        strat = tuples(just(False), integers(0, 5))
        if self.elements:
            strat |= tuples(just(True), sampled_from(self.elements))
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
        return (
            integers(self.counter - 1, self.counter + 50)
        )

    def execute_step(self, step):
        assert step >= self.counter
        self.counter = step


class GoodSet(GenericStateMachine):

    def __init__(self):
        self.stuff = set()

    def steps(self):
        return tuples(booleans(), integers())

    def execute_step(self, step):
        delete, value = step
        if delete:
            self.stuff.discard(value)
        else:
            self.stuff.add(value)
        assert delete == (value not in self.stuff)


Leaf = namedtuple(u'Leaf', (u'label',))
Split = namedtuple(u'Split', (u'left', u'right'))


class BalancedTrees(RuleBasedStateMachine):
    trees = u'BinaryTree'

    @rule(target=trees, x=booleans())
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
    charges = Bundle(u'charges')

    @rule(targets=(charges,), child=charges)
    def charge(self, child):
        return DepthCharge(child)

    @rule(targets=(charges,))
    def none_charge(self):
        return DepthCharge(None)

    @rule(check=charges)
    def is_not_too_deep(self, check):
        assert check.depth < 3


class MultipleRulesSameFuncMachine(RuleBasedStateMachine):

    def myfunc(self, data):
        print_unicode(data)

    rule1 = rule(data=just(u"rule1data"))(myfunc)
    rule2 = rule(data=just(u"rule2data"))(myfunc)


class PreconditionMachine(RuleBasedStateMachine):
    num = 0

    @rule()
    def add_one(self):
        self.num += 1

    @rule()
    def set_to_zero(self):
        self.num = 0

    @rule(num=integers())
    @precondition(lambda self: self.num != 0)
    def div_by_precondition_after(self, num):
        self.num = num / self.num

    @precondition(lambda self: self.num != 0)
    @rule(num=integers())
    def div_by_precondition_before(self, num):
        self.num = num / self.num


class RoseTreeStateMachine(RuleBasedStateMachine):
    nodes = Bundle('nodes')

    @rule(target=nodes, source=lists(nodes))
    def bunch(self, source):
        return source

    @rule(source=nodes)
    def shallow(self, source):
        def d(ls):
            if not ls:
                return 0
            else:
                return 1 + max(map(d, ls))
        assert d(source) <= 5


class NotTheLastMachine(RuleBasedStateMachine):
    stuff = Bundle('stuff')

    def __init__(self):
        super(NotTheLastMachine, self).__init__()
        self.last = None
        self.bye_called = False

    @rule(target=stuff)
    def hi(self):
        result = object()
        self.last = result
        return result

    @precondition(lambda self: not self.bye_called)
    @rule(v=stuff)
    def bye(self, v):
        assert v == self.last
        self.bye_called = True

bad_machines = (
    OrderedStateMachine, SetStateMachine, BalancedTrees,
    DepthMachine, RoseTreeStateMachine, NotTheLastMachine,
)

for m in bad_machines:
    m.TestCase.settings = Settings(
        m.TestCase.settings, max_examples=1000, max_iterations=2000
    )


cheap_bad_machines = list(bad_machines)
cheap_bad_machines.remove(BalancedTrees)


with_cheap_bad_machines = pytest.mark.parametrize(
    u'machine',
    cheap_bad_machines, ids=[t.__name__ for t in cheap_bad_machines]
)


@pytest.mark.parametrize(
    u'machine',
    bad_machines, ids=[t.__name__ for t in bad_machines]
)
def test_bad_machines_fail(machine):
    test_class = machine.TestCase
    try:
        with capture_out() as o:
            with raises(AssertionError):
                test_class().runTest()
    except Exception:
        print_unicode(o.getvalue())
        raise
    v = o.getvalue()
    print_unicode(v)
    assert u'Step #1' in v
    assert u'Step #50' not in v


def test_multiple_rules_same_func():
    test_class = MultipleRulesSameFuncMachine.TestCase
    with capture_out() as o:
        test_class().runTest()
    output = o.getvalue()
    assert 'rule1data' in output
    assert 'rule2data' in output


class GivenLikeStateMachine(GenericStateMachine):

    def steps(self):
        return lists(booleans(), average_size=25.0)

    def execute_step(self, step):
        assume(any(step))


def test_can_get_test_case_off_machine_instance():
    assert GoodSet().TestCase is GoodSet().TestCase
    assert GoodSet().TestCase is not None


class FlakyDrawLessMachine(GenericStateMachine):

    def steps(self):
        cb = current_build_context()
        if cb.is_final:
            return binary(min_size=1, max_size=1)
        else:
            return binary(min_size=1024, max_size=1024)

    def execute_step(self, step):
        cb = current_build_context()
        if not cb.is_final:
            assert 0 not in bytearray(step)


def test_flaky_draw_less_raises_flaky():
    with raises(Flaky):
        FlakyDrawLessMachine.TestCase().runTest()


class FlakyStateMachine(GenericStateMachine):

    def steps(self):
        return just(())

    def execute_step(self, step):
        assert not any(
            t[3] == u'find_breaking_runner'
            for t in inspect.getouterframes(inspect.currentframe())
        )


def test_flaky_raises_flaky():
    with raises(Flaky):
        FlakyStateMachine.TestCase().runTest()


class FlakyRatchettingMachine(GenericStateMachine):
    ratchet = 0

    def steps(self):
        FlakyRatchettingMachine.ratchet += 1
        n = FlakyRatchettingMachine.ratchet
        return lists(integers(), min_size=n, max_size=n)

    def execute_step(self, step):
        assert False


def test_ratchetting_raises_flaky():
    with raises(Flaky):
        FlakyRatchettingMachine.TestCase().runTest()


def test_empty_machine_is_invalid():
    class EmptyMachine(RuleBasedStateMachine):
        pass

    with raises(InvalidDefinition):
        EmptyMachine.TestCase().runTest()


def test_machine_with_no_terminals_is_invalid():
    class NonTerminalMachine(RuleBasedStateMachine):

        @rule(value=Bundle(u'hi'))
        def bye(self, hi):
            pass

    with raises(InvalidDefinition):
        NonTerminalMachine.TestCase().runTest()


class DynamicMachine(RuleBasedStateMachine):

    @rule(value=Bundle(u'hi'))
    def test_stuff(x):
        pass

DynamicMachine.define_rule(
    targets=(), function=lambda self: 1, arguments={}
)


class IntAdder(RuleBasedStateMachine):
    pass

IntAdder.define_rule(
    targets=(u'ints',), function=lambda self, x: x, arguments={
        u'x': integers()
    }
)

IntAdder.define_rule(
    targets=(u'ints',), function=lambda self, x, y: x, arguments={
        u'x': integers(), u'y': Bundle(u'ints'),
    }
)


class ChoosingMachine(GenericStateMachine):

    def steps(self):
        return choices()

    def execute_step(self, choices):
        choices([1, 2, 3])


with Settings(max_examples=10):
    TestChoosingMachine = ChoosingMachine.TestCase
    TestGoodSets = GoodSet.TestCase
    TestGivenLike = GivenLikeStateMachine.TestCase
    TestDynamicMachine = DynamicMachine.TestCase
    TestIntAdder = IntAdder.TestCase
    TestPrecondition = PreconditionMachine.TestCase


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
        Foo.TestCase.settings = Settings(
            Foo.TestCase.settings, max_examples=1000000)
    assert s.max_examples == orig


def test_minimizes_errors_in_teardown():
    class Foo(GenericStateMachine):

        def __init__(self):
            self.counter = 0

        def steps(self):
            return tuples()

        def execute_step(self, value):
            self.counter += 1

        def teardown(self):
            assert not self.counter

    runner = Foo.find_breaking_runner()

    f = Foo()
    with raises(AssertionError):
        runner.run(f, print_steps=True)
    assert f.counter == 1


class RequiresInit(GenericStateMachine):

    def __init__(self, threshold):
        super(RequiresInit, self).__init__()
        self.threshold = threshold

    def steps(self):
        return integers()

    def execute_step(self, value):
        if value > self.threshold:
            raise ValueError(u'%d is too high' % (value,))


def test_can_use_factory_for_tests():
    with raises(ValueError):
        run_state_machine_as_test(lambda: RequiresInit(42))


class FailsEventually(GenericStateMachine):

    def __init__(self):
        super(FailsEventually, self).__init__()
        self.counter = 0

    def steps(self):
        return none()

    def execute_step(self, _):
        self.counter += 1
        assert self.counter < 10

FailsEventually.TestCase.settings = Settings(
    FailsEventually.TestCase.settings, stateful_step_count=5)

TestDoesNotFail = FailsEventually.TestCase


def test_can_explicitly_pass_settings():
    try:
        FailsEventually.TestCase.settings = Settings(
            FailsEventually.TestCase.settings, stateful_step_count=15)
        run_state_machine_as_test(
            FailsEventually, settings=Settings(
                stateful_step_count=2,
            ))
    finally:
        FailsEventually.TestCase.settings = Settings(
            FailsEventually.TestCase.settings, stateful_step_count=5)


def test_saves_failing_example_in_database():
    db = ExampleDatabase()
    with raises(AssertionError):
        run_state_machine_as_test(
            SetStateMachine, Settings(database=db))
    assert len(list(db.data.keys())) == 1


def test_can_run_with_no_db():
    with raises(AssertionError):
        run_state_machine_as_test(
            SetStateMachine, Settings(database=None))


def test_stateful_double_rule_is_forbidden(recwarn):
    with pytest.raises(InvalidDefinition):
        class DoubleRuleMachine(RuleBasedStateMachine):

            @rule(num=just(1))
            @rule(num=just(2))
            def whatevs(self, num):
                pass


def test_can_explicitly_call_functions_when_precondition_not_satisfied():
    class BadPrecondition(RuleBasedStateMachine):

        def __init__(self):
            super(BadPrecondition, self).__init__()

        @precondition(lambda self: False)
        @rule()
        def test_blah(self):
            raise ValueError()

        @rule()
        def test_foo(self):
            self.test_blah()

    with pytest.raises(ValueError):
        run_state_machine_as_test(BadPrecondition)
