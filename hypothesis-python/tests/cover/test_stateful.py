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

import base64
from collections import defaultdict, namedtuple

import pytest
from _pytest.outcomes import Failed, Skipped

from hypothesis import __version__, reproduce_failure, seed, settings as Settings
from hypothesis.control import current_build_context
from hypothesis.database import ExampleDatabase
from hypothesis.errors import DidNotReproduce, Flaky, InvalidArgument, InvalidDefinition
from hypothesis.internal.compat import print_unicode
from hypothesis.stateful import (
    Bundle,
    GenericStateMachine,
    RuleBasedStateMachine,
    consumes,
    initialize,
    invariant,
    multiple,
    precondition,
    rule,
    run_state_machine_as_test,
)
from hypothesis.strategies import (
    binary,
    booleans,
    integers,
    just,
    lists,
    none,
    sampled_from,
    tuples,
)
from tests.common.utils import capture_out, checks_deprecated_behaviour, raises

NO_BLOB_SETTINGS = Settings(print_blob=False)


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
        return integers(self.counter - 1, self.counter + 50)

    def execute_step(self, step):
        assert step >= self.counter
        self.counter = step


Leaf = namedtuple(u"Leaf", (u"label",))
Split = namedtuple(u"Split", (u"left", u"right"))


class BalancedTrees(RuleBasedStateMachine):
    trees = Bundle(u"BinaryTree")

    @rule(target=trees, x=booleans())
    def leaf(self, x):
        return Leaf(x)

    @rule(target=trees, left=trees, right=trees)
    def split(self, left, right):
        return Split(left, right)

    @rule(tree=trees)
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
    charges = Bundle(u"charges")

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
    nodes = Bundle("nodes")

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
    stuff = Bundle("stuff")

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


class PopulateMultipleTargets(RuleBasedStateMachine):
    b1 = Bundle("b1")
    b2 = Bundle("b2")

    @rule(targets=(b1, b2))
    def populate(self):
        return 1

    @rule(x=b1, y=b2)
    def fail(self, x, y):
        assert False


bad_machines = (
    BalancedTrees,
    DepthMachine,
    RoseTreeStateMachine,
    NotTheLastMachine,
    PopulateMultipleTargets,
)

for m in bad_machines:
    m.TestCase.settings = Settings(m.TestCase.settings, max_examples=1000)


cheap_bad_machines = list(bad_machines)
cheap_bad_machines.remove(BalancedTrees)


with_cheap_bad_machines = pytest.mark.parametrize(
    u"machine", cheap_bad_machines, ids=[t.__name__ for t in cheap_bad_machines]
)


@pytest.mark.parametrize(
    u"machine", bad_machines, ids=[t.__name__ for t in bad_machines]
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
    steps = [l for l in v.splitlines() if "Step " in l or "state." in l]
    assert 1 <= len(steps) <= 50


def test_multiple_rules_same_func():
    test_class = MultipleRulesSameFuncMachine.TestCase
    with capture_out() as o:
        test_class().runTest()
    output = o.getvalue()
    assert "rule1data" in output
    assert "rule2data" in output


def test_can_get_test_case_off_machine_instance():
    assert SetStateMachine().TestCase is SetStateMachine().TestCase
    assert SetStateMachine().TestCase is not None


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


@checks_deprecated_behaviour
def test_flaky_draw_less_raises_flaky():
    with raises(Flaky):
        FlakyDrawLessMachine.TestCase().runTest()


class FlakyStateMachine(GenericStateMachine):
    def steps(self):
        return just(())

    def execute_step(self, step):
        assert current_build_context().is_final


@checks_deprecated_behaviour
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


class MachineWithConsumingRule(RuleBasedStateMachine):
    b1 = Bundle("b1")
    b2 = Bundle("b2")

    def __init__(self):
        self.created_counter = 0
        self.consumed_counter = 0
        super(MachineWithConsumingRule, self).__init__()

    @invariant()
    def bundle_length(self):
        assert len(self.bundle("b1")) == self.created_counter - self.consumed_counter

    @rule(target=b1)
    def populate_b1(self):
        self.created_counter += 1
        return self.created_counter

    @rule(target=b2, consumed=consumes(b1))
    def depopulate_b1(self, consumed):
        self.consumed_counter += 1
        return consumed

    @rule(consumed=lists(consumes(b1)))
    def depopulate_b1_multiple(self, consumed):
        self.consumed_counter += len(consumed)

    @rule(value1=b1, value2=b2)
    def check(self, value1, value2):
        assert value1 != value2


TestMachineWithConsumingRule = MachineWithConsumingRule.TestCase


def test_multiple():
    none = multiple()
    some = multiple(1, 2.01, "3", b"4", 5)
    assert len(none.values) == 0 and len(some.values) == 5
    assert all(value in some.values for value in (1, 2.01, "3", b"4", 5))


class MachineUsingMultiple(RuleBasedStateMachine):
    b = Bundle("b")

    def __init__(self):
        self.expected_bundle_length = 0
        super(MachineUsingMultiple, self).__init__()

    @invariant()
    def bundle_length(self):
        assert len(self.bundle("b")) == self.expected_bundle_length

    @rule(target=b, items=lists(elements=integers(), max_size=10))
    def populate_bundle(self, items):
        self.expected_bundle_length += len(items)
        return multiple(*items)

    @rule(target=b)
    def do_not_populate(self):
        return multiple()


TestMachineUsingMultiple = MachineUsingMultiple.TestCase


def test_multiple_variables_printed():
    class ProducesMultiple(RuleBasedStateMachine):
        b = Bundle("b")

        @initialize(target=b)
        def populate_bundle(self):
            return multiple(1, 2)

        @rule()
        def fail_fast(self):
            assert False

    with capture_out() as o:
        # The state machine must raise an exception for the
        # falsifying example to be printed.
        with raises(AssertionError):
            run_state_machine_as_test(ProducesMultiple)

    # This is tightly coupled to the output format of the step printing.
    # The first line is "Falsifying Example:..." the second is creating
    # the state machine, the third is calling the "initialize" method.
    assignment_line = o.getvalue().split("\n")[2]
    # 'populate_bundle()' returns 2 values, so should be
    # expanded to 2 variables.
    assert assignment_line == "v1, v2 = state.populate_bundle()"


def test_no_variables_printed():
    class ProducesNoVariables(RuleBasedStateMachine):
        b = Bundle("b")

        @initialize(target=b)
        def populate_bundle(self):
            return multiple()

        @rule()
        def fail_fast(self):
            assert False

    with capture_out() as o:
        # The state machine must raise an exception for the
        # falsifying example to be printed.
        with raises(AssertionError):
            run_state_machine_as_test(ProducesNoVariables)

    # This is tightly coupled to the output format of the step printing.
    # The first line is "Falsifying Example:..." the second is creating
    # the state machine, the third is calling the "initialize" method.
    assignment_line = o.getvalue().split("\n")[2]
    # 'populate_bundle()' returns 0 values, so there should be no
    # variable assignment.
    assert assignment_line == "state.populate_bundle()"


def test_consumes_typecheck():
    with pytest.raises(TypeError):
        consumes(integers())


@checks_deprecated_behaviour
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
        @rule(value=Bundle(u"hi"))
        def bye(self, hi):
            pass

    with raises(InvalidDefinition):
        NonTerminalMachine.TestCase().runTest()


class DynamicMachine(RuleBasedStateMachine):
    @rule(value=Bundle(u"hi"))
    def test_stuff(x):
        pass


DynamicMachine.define_rule(targets=(), function=lambda self: 1, arguments={})


class IntAdder(RuleBasedStateMachine):
    pass


IntAdder.define_rule(
    targets=(u"ints",), function=lambda self, x: x, arguments={u"x": integers()}
)

IntAdder.define_rule(
    targets=(u"ints",),
    function=lambda self, x, y: x,
    arguments={u"x": integers(), u"y": Bundle(u"ints")},
)


TestDynamicMachine = DynamicMachine.TestCase
TestIntAdder = IntAdder.TestCase
TestPrecondition = PreconditionMachine.TestCase


for test_case in (TestDynamicMachine, TestIntAdder, TestPrecondition):
    test_case.settings = Settings(test_case.settings, max_examples=10)


def test_picks_up_settings_at_first_use_of_testcase():
    assert TestDynamicMachine.settings.max_examples == 10


def test_new_rules_are_picked_up_before_and_after_rules_call():
    class Foo(RuleBasedStateMachine):
        pass

    Foo.define_rule(targets=(), function=lambda self: 1, arguments={})
    assert len(Foo.rules()) == 1
    Foo.define_rule(targets=(), function=lambda self: 2, arguments={})
    assert len(Foo.rules()) == 2


@checks_deprecated_behaviour
def test_minimizes_errors_in_teardown():
    counter = [0]

    class Foo(GenericStateMachine):
        def __init__(self):
            counter[0] = 0

        def steps(self):
            return tuples()

        def execute_step(self, value):
            counter[0] += 1

        def teardown(self):
            assert not counter[0]

    with raises(AssertionError):
        run_state_machine_as_test(Foo)
    assert counter[0] == 1


class RequiresInit(GenericStateMachine):
    def __init__(self, threshold):
        super(RequiresInit, self).__init__()
        self.threshold = threshold

    def steps(self):
        return integers()

    def execute_step(self, value):
        if value > self.threshold:
            raise ValueError(u"%d is too high" % (value,))


@checks_deprecated_behaviour
def test_can_use_factory_for_tests():
    with raises(ValueError):
        run_state_machine_as_test(lambda: RequiresInit(42))


@Settings(stateful_step_count=5)
class FailsEventually(GenericStateMachine):
    def __init__(self):
        super(FailsEventually, self).__init__()
        self.counter = 0

    def steps(self):
        return none()

    def execute_step(self, _):
        self.counter += 1
        assert self.counter < 10


@checks_deprecated_behaviour
def test_can_explicitly_pass_settings():
    run_state_machine_as_test(FailsEventually)
    try:
        FailsEventually.TestCase.settings = Settings(
            FailsEventually.TestCase.settings, stateful_step_count=15
        )
        run_state_machine_as_test(
            FailsEventually, settings=Settings(stateful_step_count=2)
        )
    finally:
        FailsEventually.TestCase.settings = Settings(
            FailsEventually.TestCase.settings, stateful_step_count=5
        )


def test_settings_argument_is_validated():
    with pytest.raises(InvalidArgument):
        run_state_machine_as_test(FailsEventually, settings=object())


def test_runner_that_checks_factory_produced_a_machine():
    with pytest.raises(InvalidArgument):
        run_state_machine_as_test(object)


def test_settings_attribute_is_validated():
    real_settings = FailsEventually.TestCase.settings
    try:
        FailsEventually.TestCase.settings = object()
        with pytest.raises(InvalidArgument):
            run_state_machine_as_test(FailsEventually)
    finally:
        FailsEventually.TestCase.settings = real_settings


@checks_deprecated_behaviour
def test_saves_failing_example_in_database():
    db = ExampleDatabase(":memory:")
    with raises(AssertionError):
        run_state_machine_as_test(
            SetStateMachine, Settings(database=db, max_examples=100)
        )
    assert any(list(db.data.values()))


@checks_deprecated_behaviour
def test_can_run_with_no_db():
    with raises(AssertionError):
        run_state_machine_as_test(SetStateMachine, Settings(database=None))


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


def test_invariant():
    """If an invariant raise an exception, the exception is propagated."""

    class Invariant(RuleBasedStateMachine):
        def __init__(self):
            super(Invariant, self).__init__()

        @invariant()
        def test_blah(self):
            raise ValueError()

        @rule()
        def do_stuff(self):
            pass

    with pytest.raises(ValueError):
        run_state_machine_as_test(Invariant)


def test_no_double_invariant():
    """The invariant decorator can't be applied multiple times to a single
    function."""
    with raises(InvalidDefinition):

        class Invariant(RuleBasedStateMachine):
            def __init__(self):
                super(Invariant, self).__init__()

            @invariant()
            @invariant()
            def test_blah(self):
                pass

            @rule()
            def do_stuff(self):
                pass


def test_invariant_precondition():
    """If an invariant precodition isn't met, the invariant isn't run.

    The precondition decorator can be applied in any order.
    """

    class Invariant(RuleBasedStateMachine):
        def __init__(self):
            super(Invariant, self).__init__()

        @invariant()
        @precondition(lambda _: False)
        def an_invariant(self):
            raise ValueError()

        @precondition(lambda _: False)
        @invariant()
        def another_invariant(self):
            raise ValueError()

        @rule()
        def do_stuff(self):
            pass

    run_state_machine_as_test(Invariant)


def test_multiple_invariants():
    """If multiple invariants are present, they all get run."""

    class Invariant(RuleBasedStateMachine):
        def __init__(self):
            super(Invariant, self).__init__()
            self.first_invariant_ran = False

        @invariant()
        def invariant_1(self):
            self.first_invariant_ran = True

        @precondition(lambda self: self.first_invariant_ran)
        @invariant()
        def invariant_2(self):
            raise ValueError()

        @rule()
        def do_stuff(self):
            pass

    with pytest.raises(ValueError):
        run_state_machine_as_test(Invariant)


def test_explicit_invariant_call_with_precondition():
    """Invariants can be called explicitly even if their precondition is not
    satisfied."""

    class BadPrecondition(RuleBasedStateMachine):
        def __init__(self):
            super(BadPrecondition, self).__init__()

        @precondition(lambda self: False)
        @invariant()
        def test_blah(self):
            raise ValueError()

        @rule()
        def test_foo(self):
            self.test_blah()

    with pytest.raises(ValueError):
        run_state_machine_as_test(BadPrecondition)


def test_invariant_checks_initial_state():
    """Invariants are checked before any rules run."""

    class BadPrecondition(RuleBasedStateMachine):
        def __init__(self):
            super(BadPrecondition, self).__init__()
            self.num = 0

        @invariant()
        def test_blah(self):
            if self.num == 0:
                raise ValueError()

        @rule()
        def test_foo(self):
            self.num += 1

    with pytest.raises(ValueError):
        run_state_machine_as_test(BadPrecondition)


def test_always_runs_at_least_one_step():
    class CountSteps(RuleBasedStateMachine):
        def __init__(self):
            super(CountSteps, self).__init__()
            self.count = 0

        @rule()
        def do_something(self):
            self.count += 1

        def teardown(self):
            assert self.count > 0

    run_state_machine_as_test(CountSteps)


def test_removes_needless_steps():
    """Regression test from an example based on
    tests/nocover/test_database_agreement.py, but without the expensive bits.
    Comparing two database implementations in which deletion is broken, so as
    soon as a key/value pair is successfully deleted the test will now fail if
    you ever check that key.

    The main interesting feature of this is that it has a lot of
    opportunities to generate keys and values before it actually fails,
    but will still fail with very high probability.
    """

    @Settings(derandomize=True, max_examples=1000)
    class IncorrectDeletion(RuleBasedStateMachine):
        def __init__(self):
            super(IncorrectDeletion, self).__init__()
            self.__saved = defaultdict(set)
            self.__deleted = defaultdict(set)

        keys = Bundle("keys")
        values = Bundle("values")

        @rule(target=keys, k=binary())
        def k(self, k):
            return k

        @rule(target=values, v=binary())
        def v(self, v):
            return v

        @rule(k=keys, v=values)
        def save(self, k, v):
            self.__saved[k].add(v)

        @rule(k=keys, v=values)
        def delete(self, k, v):
            if v in self.__saved[k]:
                self.__deleted[k].add(v)

        @rule(k=keys)
        def values_agree(self, k):
            assert not self.__deleted[k]

    with capture_out() as o:
        with pytest.raises(AssertionError):
            run_state_machine_as_test(IncorrectDeletion)

    assert o.getvalue().count(" = state.k(") == 1
    assert o.getvalue().count(" = state.v(") == 1


def test_prints_equal_values_with_correct_variable_name():
    @Settings(max_examples=100)
    class MovesBetweenBundles(RuleBasedStateMachine):
        b1 = Bundle("b1")
        b2 = Bundle("b2")

        @rule(target=b1)
        def create(self):
            return []

        @rule(target=b2, source=b1)
        def transfer(self, source):
            return source

        @rule(source=b2)
        def fail(self, source):
            assert False

    with capture_out() as o:
        with pytest.raises(AssertionError):
            run_state_machine_as_test(MovesBetweenBundles)

    result = o.getvalue()
    for m in ["create", "transfer", "fail"]:
        assert result.count("state." + m) == 1
    assert "v1 = state.create()" in result
    assert "v2 = state.transfer(source=v1)" in result
    assert "state.fail(source=v2)" in result


def test_initialize_rule():
    class WithInitializeRules(RuleBasedStateMachine):
        initialized = []

        @initialize()
        def initialize_a(self):
            self.initialized.append("a")

        @initialize()
        def initialize_b(self):
            self.initialized.append("b")

        @initialize()
        def initialize_c(self):
            self.initialized.append("c")

        @rule()
        def fail_fast(self):
            assert False

    with capture_out() as o:
        with pytest.raises(AssertionError):
            run_state_machine_as_test(WithInitializeRules)

    assert set(WithInitializeRules.initialized[-3:]) == {"a", "b", "c"}
    result = o.getvalue().splitlines()[1:]
    assert result[0] == "state = WithInitializeRules()"
    # Initialize rules call order is shuffled
    assert {result[1], result[2], result[3]} == {
        "state.initialize_a()",
        "state.initialize_b()",
        "state.initialize_c()",
    }
    assert result[4] == "state.fail_fast()"
    assert result[5] == "state.teardown()"


def test_initialize_rule_populate_bundle():
    class WithInitializeBundleRules(RuleBasedStateMachine):
        a = Bundle("a")

        @initialize(target=a, dep=just("dep"))
        def initialize_a(self, dep):
            return "a v1 with (%s)" % dep

        @rule(param=a)
        def fail_fast(self, param):
            assert False

    WithInitializeBundleRules.TestCase.settings = NO_BLOB_SETTINGS
    with capture_out() as o:
        with pytest.raises(AssertionError):
            run_state_machine_as_test(WithInitializeBundleRules)

    result = o.getvalue()
    assert (
        result
        == """\
Falsifying example: run_state_machine(\
factory=WithInitializeBundleRules, data=data(...))
state = WithInitializeBundleRules()
v1 = state.initialize_a(dep='dep')
state.fail_fast(param=v1)
state.teardown()
"""
    )


def test_initialize_rule_dont_mix_with_precondition():
    with pytest.raises(InvalidDefinition) as exc:

        class BadStateMachine(RuleBasedStateMachine):
            @precondition(lambda self: True)
            @initialize()
            def initialize(self):
                pass

    assert "An initialization rule cannot have a precondition." in str(exc.value)

    # Also test decorator application in reverse order

    with pytest.raises(InvalidDefinition) as exc:

        class BadStateMachineReverseOrder(RuleBasedStateMachine):
            @initialize()
            @precondition(lambda self: True)
            def initialize(self):
                pass

    assert "An initialization rule cannot have a precondition." in str(exc.value)


def test_initialize_rule_dont_mix_with_regular_rule():
    with pytest.raises(InvalidDefinition) as exc:

        class BadStateMachine(RuleBasedStateMachine):
            @rule()
            @initialize()
            def initialize(self):
                pass

    assert "A function cannot be used for two distinct rules." in str(exc.value)


def test_initialize_rule_cannot_be_double_applied():
    with pytest.raises(InvalidDefinition) as exc:

        class BadStateMachine(RuleBasedStateMachine):
            @initialize()
            @initialize()
            def initialize(self):
                pass

    assert "A function cannot be used for two distinct rules." in str(exc.value)


def test_initialize_rule_in_state_machine_with_inheritance():
    class ParentStateMachine(RuleBasedStateMachine):
        initialized = []

        @initialize()
        def initialize_a(self):
            self.initialized.append("a")

    class ChildStateMachine(ParentStateMachine):
        @initialize()
        def initialize_b(self):
            self.initialized.append("b")

        @rule()
        def fail_fast(self):
            assert False

    with capture_out() as o:
        with pytest.raises(AssertionError):
            run_state_machine_as_test(ChildStateMachine)

    assert set(ChildStateMachine.initialized[-2:]) == {"a", "b"}
    result = o.getvalue().splitlines()[1:]
    assert result[0] == "state = ChildStateMachine()"
    # Initialize rules call order is shuffled
    assert {result[1], result[2]} == {"state.initialize_a()", "state.initialize_b()"}
    assert result[3] == "state.fail_fast()"
    assert result[4] == "state.teardown()"


def test_can_manually_call_initialize_rule():
    class StateMachine(RuleBasedStateMachine):
        initialize_called_counter = 0

        @initialize()
        def initialize(self):
            self.initialize_called_counter += 1
            return self.initialize_called_counter

        @rule()
        def fail_eventually(self):
            assert self.initialize() <= 2

    StateMachine.TestCase.settings = NO_BLOB_SETTINGS
    with capture_out() as o:
        with pytest.raises(AssertionError):
            run_state_machine_as_test(StateMachine)

    result = o.getvalue()
    assert (
        result
        == """\
Falsifying example: run_state_machine(factory=StateMachine, data=data(...))
state = StateMachine()
state.initialize()
state.fail_eventually()
state.fail_eventually()
state.teardown()
"""
    )


def test_new_initialize_rules_are_picked_up_before_and_after_rules_call():
    class Foo(RuleBasedStateMachine):
        pass

    Foo.define_initialize_rule(targets=(), function=lambda self: 1, arguments={})
    assert len(Foo.initialize_rules()) == 1
    Foo.define_initialize_rule(targets=(), function=lambda self: 2, arguments={})
    assert len(Foo.initialize_rules()) == 2


def test_steps_printed_despite_pytest_fail(capsys):
    # Test for https://github.com/HypothesisWorks/hypothesis/issues/1372
    class RaisesProblem(RuleBasedStateMachine):
        @rule()
        def oops(self):
            pytest.fail()

    with pytest.raises(Failed):
        run_state_machine_as_test(RaisesProblem)
    out, _ = capsys.readouterr()
    assert (
        """\
Falsifying example: run_state_machine(factory=RaisesProblem, data=data(...))
state = RaisesProblem()
state.oops()
state.teardown()
"""
        in out
    )


def test_steps_not_printed_with_pytest_skip(capsys):
    class RaisesProblem(RuleBasedStateMachine):
        @rule()
        def skip_whole_test(self):
            pytest.skip()

    with pytest.raises(Skipped):
        run_state_machine_as_test(RaisesProblem)
    out, _ = capsys.readouterr()
    assert "state" not in out


@checks_deprecated_behaviour
def test_rule_deprecation_targets_and_target():
    k, v = Bundle("k"), Bundle("v")
    rule(targets=(k,), target=v)


@checks_deprecated_behaviour
def test_rule_deprecation_bundle_by_name():
    Bundle("k")
    rule(target="k")


def test_rule_non_bundle_target():
    with pytest.raises(InvalidArgument):
        rule(target=integers())


def test_rule_non_bundle_target_oneof():
    k, v = Bundle("k"), Bundle("v")
    pattern = r".+ `one_of(a, b)` or `a | b` .+"
    with pytest.raises(InvalidArgument, match=pattern):
        rule(target=k | v)


def test_uses_seed(capsys):
    @seed(0)
    class TrivialMachine(RuleBasedStateMachine):
        @rule()
        def oops(self):
            assert False

    with pytest.raises(AssertionError):
        run_state_machine_as_test(TrivialMachine)
    out, _ = capsys.readouterr()
    assert "@seed" not in out


def test_reproduce_failure_works():
    @reproduce_failure(__version__, base64.b64encode(b"\0\0\0"))
    class TrivialMachine(RuleBasedStateMachine):
        @rule()
        def oops(self):
            assert False

    with pytest.raises(AssertionError):
        run_state_machine_as_test(TrivialMachine)


def test_reproduce_failure_fails_if_no_error():
    @reproduce_failure(__version__, base64.b64encode(b"\0\0\0"))
    class TrivialMachine(RuleBasedStateMachine):
        @rule()
        def ok(self):
            assert True

    with pytest.raises(DidNotReproduce):
        run_state_machine_as_test(TrivialMachine)
