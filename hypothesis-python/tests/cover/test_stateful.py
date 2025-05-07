# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re
from collections import defaultdict
from typing import ClassVar

import pytest
from _pytest.outcomes import Failed, Skipped
from pytest import raises

from hypothesis import (
    HealthCheck,
    Phase,
    __version__,
    reproduce_failure,
    seed,
    settings as Settings,
    strategies as st,
)
from hypothesis.control import current_build_context
from hypothesis.core import encode_failure
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.errors import DidNotReproduce, Flaky, InvalidArgument, InvalidDefinition
from hypothesis.internal.entropy import deterministic_PRNG
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    consumes,
    initialize,
    invariant,
    multiple,
    precondition,
    rule,
    run_state_machine_as_test,
)
from hypothesis.strategies import binary, data, integers, just, lists

from tests.common.utils import (
    Why,
    capture_out,
    validate_deprecation,
    xfail_on_crosshair,
)
from tests.nocover.test_stateful import DepthMachine

NO_BLOB_SETTINGS = Settings(print_blob=False, phases=tuple(Phase)[:-1])


class MultipleRulesSameFuncMachine(RuleBasedStateMachine):
    def myfunc(self, data):
        print(data)

    rule1 = rule(data=just("rule1data"))(myfunc)
    rule2 = rule(data=just("rule2data"))(myfunc)


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


TestPrecondition = PreconditionMachine.TestCase
TestPrecondition.settings = Settings(TestPrecondition.settings, max_examples=10)


def test_picks_up_settings_at_first_use_of_testcase():
    assert TestPrecondition.settings.max_examples == 10


def test_multiple_rules_same_func():
    test_class = MultipleRulesSameFuncMachine.TestCase
    with capture_out() as o:
        test_class().runTest()
    output = o.getvalue()
    assert "rule1data" in output
    assert "rule2data" in output


def test_can_get_test_case_off_machine_instance():
    assert DepthMachine().TestCase is DepthMachine().TestCase
    assert DepthMachine().TestCase is not None


class FlakyDrawLessMachine(RuleBasedStateMachine):
    @rule(d=data())
    def action(self, d):
        if current_build_context().is_final:
            d.draw(binary(min_size=1, max_size=1))
        else:
            buffer = binary(min_size=1024, max_size=1024)
            assert 0 not in buffer


def test_flaky_draw_less_raises_flaky():
    with raises(Flaky):
        FlakyDrawLessMachine.TestCase().runTest()


def test_result_is_added_to_target():
    class TargetStateMachine(RuleBasedStateMachine):
        nodes = Bundle("nodes")

        @rule(target=nodes, source=lists(nodes))
        def bunch(self, source):
            assert len(source) == 0
            return source

    test_class = TargetStateMachine.TestCase
    try:
        test_class().runTest()
        raise RuntimeError("Expected an assertion error")
    except AssertionError as err:
        notes = err.__notes__
    regularized_notes = [re.sub(r"[0-9]+", "i", note) for note in notes]
    assert "state.bunch(source=[nodes_i])" in regularized_notes


class FlakyStateMachine(RuleBasedStateMachine):
    @rule()
    def action(self):
        assert current_build_context().is_final


def test_flaky_raises_flaky():
    with raises(Flaky):
        FlakyStateMachine.TestCase().runTest()


class FlakyRatchettingMachine(RuleBasedStateMachine):
    ratchet = 0

    @rule(d=data())
    def action(self, d):
        FlakyRatchettingMachine.ratchet += 1
        n = FlakyRatchettingMachine.ratchet
        d.draw(lists(integers(), min_size=n, max_size=n))
        raise AssertionError


@Settings(
    stateful_step_count=10,
    max_examples=30,
    suppress_health_check=[HealthCheck.filter_too_much],
)  # speed this up
class MachineWithConsumingRule(RuleBasedStateMachine):
    b1 = Bundle("b1")
    b2 = Bundle("b2")

    def __init__(self):
        self.created_counter = 0
        self.consumed_counter = 0
        super().__init__()

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

    @rule(consumed=lists(consumes(b1), max_size=3))
    def depopulate_b1_multiple(self, consumed):
        self.consumed_counter += len(consumed)

    @rule(value1=b1, value2=b2)
    def check(self, value1, value2):
        assert value1 != value2


TestMachineWithConsumingRule = MachineWithConsumingRule.TestCase


def test_multiple():
    none = multiple()
    some = multiple(1, 2.01, "3", b"4", 5)
    assert len(none.values) == 0
    assert len(some.values) == 5
    assert set(some.values) == {1, 2.01, "3", b"4", 5}


class MachineUsingMultiple(RuleBasedStateMachine):
    b = Bundle("b")

    def __init__(self):
        self.expected_bundle_length = 0
        super().__init__()

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
            raise AssertionError

    with raises(AssertionError) as err:
        run_state_machine_as_test(ProducesMultiple)

    # This is tightly coupled to the output format of the step printing.
    # The first line is "Falsifying Example:..." the second is creating
    # the state machine, the third is calling the "initialize" method.
    assignment_line = err.value.__notes__[2]
    # 'populate_bundle()' returns 2 values, so should be
    # expanded to 2 variables.
    assert assignment_line == "b_0, b_1 = state.populate_bundle()"

    # Make sure MultipleResult is iterable so the printed code is valid.
    # See https://github.com/HypothesisWorks/hypothesis/issues/2311
    state = ProducesMultiple()
    b_0, b_1 = state.populate_bundle()
    with raises(AssertionError):
        state.fail_fast()


def test_multiple_variables_printed_single_element():
    # https://github.com/HypothesisWorks/hypothesis/issues/3236
    class ProducesMultiple(RuleBasedStateMachine):
        b = Bundle("b")

        @initialize(target=b)
        def populate_bundle(self):
            return multiple(1)

        @rule(b=b)
        def fail_fast(self, b):
            assert b != 1

    with raises(AssertionError) as err:
        run_state_machine_as_test(ProducesMultiple)

    assignment_line = err.value.__notes__[2]
    assert assignment_line == "(b_0,) = state.populate_bundle()"

    state = ProducesMultiple()
    (v1,) = state.populate_bundle()
    state.fail_fast((v1,))  # passes if tuple not unpacked
    with raises(AssertionError):
        state.fail_fast(v1)


def test_no_variables_printed():
    class ProducesNoVariables(RuleBasedStateMachine):
        b = Bundle("b")

        @initialize(target=b)
        def populate_bundle(self):
            return multiple()

        @rule()
        def fail_fast(self):
            raise AssertionError

    with raises(AssertionError) as err:
        run_state_machine_as_test(ProducesNoVariables)

    # This is tightly coupled to the output format of the step printing.
    # The first line is "Falsifying Example:..." the second is creating
    # the state machine, the third is calling the "initialize" method.
    assignment_line = err.value.__notes__[2]
    # 'populate_bundle()' returns 0 values, so there should be no
    # variable assignment.
    assert assignment_line == "state.populate_bundle()"


def test_consumes_typecheck():
    with pytest.raises(TypeError):
        consumes(integers())


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
        @rule(value=Bundle("hi"))
        def bye(self, hi):
            pass

    with raises(InvalidDefinition):
        NonTerminalMachine.TestCase().runTest()


def test_minimizes_errors_in_teardown():
    counter = 0

    class Foo(RuleBasedStateMachine):
        @initialize()
        def init(self):
            nonlocal counter
            counter = 0

        @rule()
        def increment(self):
            nonlocal counter
            counter += 1

        def teardown(self):
            nonlocal counter
            assert not counter

    with raises(AssertionError):
        run_state_machine_as_test(Foo)
    assert counter == 1


class RequiresInit(RuleBasedStateMachine):
    def __init__(self, threshold):
        super().__init__()
        self.threshold = threshold

    @rule(value=integers())
    def action(self, value):
        if value > self.threshold:
            raise ValueError(f"{value} is too high")


def test_can_use_factory_for_tests():
    with raises(ValueError):
        run_state_machine_as_test(
            lambda: RequiresInit(42), settings=Settings(max_examples=100)
        )


class FailsEventually(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.counter = 0

    @rule()
    def increment(self):
        self.counter += 1
        assert self.counter < 10


FailsEventually.TestCase.settings = Settings(stateful_step_count=5)


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


def test_saves_failing_example_in_database():
    db = InMemoryExampleDatabase()
    ss = Settings(
        database=db, max_examples=1000, suppress_health_check=list(HealthCheck)
    )
    with raises(AssertionError):
        run_state_machine_as_test(DepthMachine, settings=ss)
    assert any(list(db.data.values()))


def test_can_run_with_no_db():
    with deterministic_PRNG(), raises(AssertionError):
        run_state_machine_as_test(
            DepthMachine, settings=Settings(database=None, max_examples=10_000)
        )


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
            super().__init__()

        @precondition(lambda self: False)
        @rule()
        def test_blah(self):
            raise ValueError

        @rule()
        def test_foo(self):
            self.test_blah()

    with pytest.raises(ValueError):
        run_state_machine_as_test(BadPrecondition)


def test_invariant():
    """If an invariant raise an exception, the exception is propagated."""

    class Invariant(RuleBasedStateMachine):
        def __init__(self):
            super().__init__()

        @invariant()
        def test_blah(self):
            raise ValueError

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
                super().__init__()

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
            super().__init__()

        @invariant()
        @precondition(lambda _: False)
        def an_invariant(self):
            raise ValueError

        @precondition(lambda _: False)
        @invariant()
        def another_invariant(self):
            raise ValueError

        @rule()
        def do_stuff(self):
            pass

    run_state_machine_as_test(Invariant)


@pytest.mark.parametrize(
    "decorators",
    [
        (invariant(), rule()),
        (rule(), invariant()),
        (invariant(), initialize()),
        (initialize(), invariant()),
        (invariant(), precondition(lambda self: True), rule()),
        (rule(), precondition(lambda self: True), invariant()),
        (precondition(lambda self: True), invariant(), rule()),
        (precondition(lambda self: True), rule(), invariant()),
    ],
    ids=lambda x: "-".join(f.__qualname__.split(".")[0] for f in x),
)
def test_invariant_and_rule_are_incompatible(decorators):
    """It's an error to apply @invariant and @rule to the same method."""

    def method(self):
        pass

    for d in decorators[:-1]:
        method = d(method)
    with pytest.raises(InvalidDefinition):
        decorators[-1](method)


def test_invalid_rule_argument():
    """Rule kwargs that are not a Strategy are expected to raise an InvalidArgument error."""
    with pytest.raises(InvalidArgument):

        class InvalidRuleMachine(RuleBasedStateMachine):
            @rule(strategy=object())
            def do_stuff(self):
                pass


def test_invalid_initialize_argument():
    """Initialize kwargs that are not a Strategy are expected to raise an InvalidArgument error."""
    with pytest.raises(InvalidArgument):

        class InvalidInitialize(RuleBasedStateMachine):
            @initialize(strategy=object())
            def initialize(self):
                pass


def test_multiple_invariants():
    """If multiple invariants are present, they all get run."""

    class Invariant(RuleBasedStateMachine):
        def __init__(self):
            super().__init__()
            self.first_invariant_ran = False

        @invariant()
        def invariant_1(self):
            self.first_invariant_ran = True

        @precondition(lambda self: self.first_invariant_ran)
        @invariant()
        def invariant_2(self):
            raise ValueError

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
            super().__init__()

        @precondition(lambda self: False)
        @invariant()
        def test_blah(self):
            raise ValueError

        @rule()
        def test_foo(self):
            self.test_blah()

    with pytest.raises(ValueError):
        run_state_machine_as_test(BadPrecondition)


def test_invariant_checks_initial_state_if_no_initialize_rules():
    """Invariants are checked before any rules run."""

    class BadPrecondition(RuleBasedStateMachine):
        def __init__(self):
            super().__init__()
            self.num = 0

        @invariant()
        def test_blah(self):
            if self.num == 0:
                raise ValueError

        @rule()
        def test_foo(self):
            self.num += 1

    with pytest.raises(ValueError):
        run_state_machine_as_test(BadPrecondition)


def test_invariant_failling_present_in_falsifying_example():
    @Settings(print_blob=False)
    class BadInvariant(RuleBasedStateMachine):
        @initialize()
        def initialize_1(self):
            pass

        @invariant()
        def invariant_1(self):
            raise ValueError

        @rule()
        def rule_1(self):
            pass

    with pytest.raises(ValueError) as err:
        run_state_machine_as_test(BadInvariant)

    result = "\n".join(err.value.__notes__)
    assert (
        result
        == """
Falsifying example:
state = BadInvariant()
state.initialize_1()
state.invariant_1()
state.teardown()
""".strip()
    )


def test_invariant_present_in_falsifying_example():
    @Settings(print_blob=False, phases=tuple(Phase)[:-1])
    class BadRuleWithGoodInvariants(RuleBasedStateMachine):
        def __init__(self):
            super().__init__()
            self.num = 0

        @initialize()
        def initialize_1(self):
            pass

        @invariant(check_during_init=True)
        def invariant_1(self):
            pass

        @invariant(check_during_init=False)
        def invariant_2(self):
            pass

        @precondition(lambda self: self.num > 0)
        @invariant()
        def invariant_3(self):
            pass

        @rule()
        def rule_1(self):
            self.num += 1
            if self.num == 2:
                raise ValueError

    with pytest.raises(ValueError) as err:
        run_state_machine_as_test(BadRuleWithGoodInvariants)

    expected = """
Falsifying example:
state = BadRuleWithGoodInvariants()
state.invariant_1()
state.initialize_1()
state.invariant_1()
state.invariant_2()
state.rule_1()
state.invariant_1()
state.invariant_2()
state.invariant_3()
state.rule_1()
state.teardown()
""".strip()

    result = "\n".join(err.value.__notes__).strip()
    assert expected == result


def test_always_runs_at_least_one_step():
    class CountSteps(RuleBasedStateMachine):
        def __init__(self):
            super().__init__()
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

    @Settings(derandomize=True, max_examples=1000, deadline=None)
    class IncorrectDeletion(RuleBasedStateMachine):
        def __init__(self):
            super().__init__()
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

    with pytest.raises(AssertionError) as err:
        run_state_machine_as_test(IncorrectDeletion)

    result = "\n".join(err.value.__notes__)
    assert result.count(" = state.k(") == 1
    assert result.count(" = state.v(") == 1


def test_prints_equal_values_with_correct_variable_name():
    @Settings(max_examples=100, suppress_health_check=list(HealthCheck))
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
            raise AssertionError

    with pytest.raises(AssertionError) as err:
        run_state_machine_as_test(MovesBetweenBundles)

    result = "\n".join(err.value.__notes__)
    for m in ["create", "transfer", "fail"]:
        assert result.count("state." + m) == 1
    assert "b1_0 = state.create()" in result
    assert "b2_0 = state.transfer(source=b1_0)" in result
    assert "state.fail(source=b2_0)" in result


def test_initialize_rule():
    @Settings(max_examples=1000)
    class WithInitializeRules(RuleBasedStateMachine):
        initialized: ClassVar = []

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
            raise AssertionError

    with pytest.raises(AssertionError) as err:
        run_state_machine_as_test(WithInitializeRules)

    assert set(WithInitializeRules.initialized[-3:]) == {"a", "b", "c"}
    result = err.value.__notes__[1:]
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
            return f"a a_0 with ({dep})"

        @rule(param=a)
        def fail_fast(self, param):
            raise AssertionError

    WithInitializeBundleRules.TestCase.settings = NO_BLOB_SETTINGS
    with pytest.raises(AssertionError) as err:
        run_state_machine_as_test(WithInitializeBundleRules)

    result = "\n".join(err.value.__notes__)
    assert (
        result
        == """
Falsifying example:
state = WithInitializeBundleRules()
a_0 = state.initialize_a(dep='dep')
state.fail_fast(param=a_0)
state.teardown()
""".strip()
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
        initialized: ClassVar = []

        @initialize()
        def initialize_a(self):
            self.initialized.append("a")

    class ChildStateMachine(ParentStateMachine):
        @initialize()
        def initialize_b(self):
            self.initialized.append("b")

        @rule()
        def fail_fast(self):
            raise AssertionError

    with pytest.raises(AssertionError) as err:
        run_state_machine_as_test(ChildStateMachine)

    assert set(ChildStateMachine.initialized[-2:]) == {"a", "b"}
    result = err.value.__notes__[1:]
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

        @rule()
        def fail_eventually(self):
            self.initialize()
            assert self.initialize_called_counter <= 2

    StateMachine.TestCase.settings = NO_BLOB_SETTINGS
    with pytest.raises(AssertionError) as err:
        run_state_machine_as_test(StateMachine)

    result = "\n".join(err.value.__notes__)
    assert (
        result
        == """
Falsifying example:
state = StateMachine()
state.initialize()
state.fail_eventually()
state.fail_eventually()
state.teardown()
""".strip()
    )


def test_steps_printed_despite_pytest_fail():
    # Test for https://github.com/HypothesisWorks/hypothesis/issues/1372
    @Settings(print_blob=False)
    class RaisesProblem(RuleBasedStateMachine):
        @rule()
        def oops(self):
            pytest.fail("note that this raises a BaseException")

    with pytest.raises(Failed) as err:
        run_state_machine_as_test(RaisesProblem)
    assert (
        "\n".join(err.value.__notes__).strip()
        == """
Falsifying example:
state = RaisesProblem()
state.oops()
state.teardown()""".strip()
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


def test_rule_deprecation_targets_and_target():
    k, v = Bundle("k"), Bundle("v")
    with pytest.raises(InvalidArgument):
        rule(targets=(k,), target=v)


def test_rule_deprecation_bundle_by_name():
    Bundle("k")
    with pytest.raises(InvalidArgument):
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
            raise AssertionError

    with pytest.raises(AssertionError):
        run_state_machine_as_test(TrivialMachine)
    out, _ = capsys.readouterr()
    assert "@seed" not in out


def test_reproduce_failure_works():
    @reproduce_failure(__version__, encode_failure([False, 0, True]))
    class TrivialMachine(RuleBasedStateMachine):
        @rule()
        def oops(self):
            raise AssertionError

    with pytest.raises(AssertionError):
        run_state_machine_as_test(TrivialMachine, settings=Settings(print_blob=True))


def test_reproduce_failure_fails_if_no_error():
    @reproduce_failure(__version__, encode_failure([False, 0, True]))
    class TrivialMachine(RuleBasedStateMachine):
        @rule()
        def ok(self):
            pass

    with pytest.raises(DidNotReproduce):
        run_state_machine_as_test(TrivialMachine, settings=Settings(print_blob=True))


def test_cannot_have_zero_steps():
    with pytest.raises(InvalidArgument):
        Settings(stateful_step_count=0)


def test_arguments_do_not_use_names_of_return_values():
    # See https://github.com/HypothesisWorks/hypothesis/issues/2341
    class TrickyPrintingMachine(RuleBasedStateMachine):
        data = Bundle("data")

        @initialize(target=data, value=integers())
        def init_data(self, value):
            return value

        @rule(d=data)
        def mostly_fails(self, d):
            assert d == 42

    with pytest.raises(AssertionError) as err:
        run_state_machine_as_test(TrickyPrintingMachine)
    assert "data_0 = state.init_data(value=0)" in err.value.__notes__
    assert "data_0 = state.init_data(value=data_0)" not in err.value.__notes__


class TrickyInitMachine(RuleBasedStateMachine):
    @initialize()
    def init_a(self):
        self.a = 0

    @rule()
    def inc(self):
        self.a += 1

    @invariant()
    def check_a_positive(self):
        # This will fail if run before the init_a method, but without
        # @invariant(check_during_init=True) it will only run afterwards.
        assert self.a >= 0


def test_invariants_are_checked_after_init_steps():
    run_state_machine_as_test(TrickyInitMachine)


def test_invariants_can_be_checked_during_init_steps():
    class UndefinedMachine(TrickyInitMachine):
        @invariant(check_during_init=True)
        def check_a_defined(self):
            # This will fail because `a` is undefined before the init rule.
            self.a

    with pytest.raises(AttributeError):
        run_state_machine_as_test(UndefinedMachine)


def test_check_during_init_must_be_boolean():
    invariant(check_during_init=False)
    invariant(check_during_init=True)
    with pytest.raises(InvalidArgument):
        invariant(check_during_init="not a bool")


def test_deprecated_target_consumes_bundle():
    # It would be nicer to raise this error at runtime, but the internals make
    # this sadly impractical.  Most InvalidDefinition errors happen at, well,
    # definition-time already anyway, so it's not *worse* than the status quo.
    with validate_deprecation():
        rule(target=consumes(Bundle("b")))


@Settings(stateful_step_count=5)
class MinStepsMachine(RuleBasedStateMachine):
    @initialize()
    def init_a(self):
        self.a = 0

    @rule()
    def inc(self):
        self.a += 1

    @invariant()
    def not_too_many_steps(self):
        assert self.a < 10

    def teardown(self):
        assert self.a >= 2


# Replay overruns after we trigger a crosshair.util.IgnoreAttempt exception for n=3
@xfail_on_crosshair(Why.other)
def test_min_steps_argument():
    # You must pass a non-negative integer...
    for n_steps in (-1, "nan", 5.0):
        with pytest.raises(InvalidArgument):
            run_state_machine_as_test(MinStepsMachine, _min_steps=n_steps)

    # and if you do, we'll take at least that many steps
    run_state_machine_as_test(MinStepsMachine, _min_steps=3)

    # (oh, and it's OK if you ask for more than we're actually going to take)
    run_state_machine_as_test(MinStepsMachine, _min_steps=20)


class ErrorsOnClassAttributeSettings(RuleBasedStateMachine):
    settings = Settings(derandomize=True)

    @rule()
    def step(self):
        pass


def test_fails_on_settings_class_attribute():
    with pytest.raises(
        InvalidDefinition,
        match="Assigning .+ as a class attribute does nothing",
    ):
        run_state_machine_as_test(ErrorsOnClassAttributeSettings)


def test_single_target_multiple():
    class Machine(RuleBasedStateMachine):
        a = Bundle("a")

        @initialize(target=a)
        def initialize(self):
            return multiple("ret1", "ret2", "ret3")

        @rule(param=a)
        def fail_fast(self, param):
            raise AssertionError

    Machine.TestCase.settings = NO_BLOB_SETTINGS
    with pytest.raises(AssertionError) as err:
        run_state_machine_as_test(Machine)

    result = "\n".join(err.value.__notes__)
    assert (
        result
        == """
Falsifying example:
state = Machine()
a_0, a_1, a_2 = state.initialize()
state.fail_fast(param=a_2)
state.teardown()
""".strip()
    )


@pytest.mark.parametrize(
    "bundle_names,initial,repr_",
    [
        ("a", "ret1", "a_0 = state.init()"),
        ("aba", "ret1", "a_0 = b_0 = a_1 = state.init()"),
        ("a", multiple(), "state.init()"),
        ("aba", multiple(), "state.init()"),
        ("a", multiple("ret1"), "(a_0,) = state.init()"),
        ("aba", multiple("ret1"), "(a_0,) = (b_0,) = (a_1,) = state.init()"),
        ("a", multiple("ret1", "ret2"), "a_0, a_1 = state.init()"),
        (
            "aba",
            multiple("ret1", "ret2"),
            "\n".join(  # noqa: FLY002  # no, f-string is not more readable
                [
                    "a_0, a_1 = state.init()",
                    "b_0, b_1 = a_0, a_1",
                    "a_2, a_3 = a_0, a_1",
                ]
            ),
        ),
    ],
)
def test_targets_repr(bundle_names, initial, repr_):
    bundles = {name: Bundle(name) for name in bundle_names}

    class Machine(RuleBasedStateMachine):

        @initialize(targets=[bundles[name] for name in bundle_names])
        def init(self):
            return initial

        @rule()
        def fail_fast(self):
            raise AssertionError

    Machine.TestCase.settings = NO_BLOB_SETTINGS
    with pytest.raises(AssertionError) as err:
        run_state_machine_as_test(Machine)

    result = "\n".join(err.value.__notes__)
    assert (
        result
        == f"""
Falsifying example:
state = Machine()
{repr_}
state.fail_fast()
state.teardown()
""".strip()
    )


def test_multiple_targets():
    class Machine(RuleBasedStateMachine):
        a = Bundle("a")
        b = Bundle("b")

        @initialize(targets=(a, b))
        def initialize(self):
            return multiple("ret1", "ret2", "ret3")

        @rule(
            a1=consumes(a),
            a2=consumes(a),
            a3=consumes(a),
            b1=consumes(b),
            b2=consumes(b),
            b3=consumes(b),
        )
        def fail_fast(self, a1, a2, a3, b1, b2, b3):
            raise AssertionError

    Machine.TestCase.settings = NO_BLOB_SETTINGS
    with pytest.raises(AssertionError) as err:
        run_state_machine_as_test(Machine)

    result = "\n".join(err.value.__notes__)
    assert (
        result
        == """
Falsifying example:
state = Machine()
a_0, a_1, a_2 = state.initialize()
b_0, b_1, b_2 = a_0, a_1, a_2
state.fail_fast(a1=a_2, a2=a_1, a3=a_0, b1=b_2, b2=b_1, b3=b_0)
state.teardown()
""".strip()
    )


def test_multiple_common_targets():
    class Machine(RuleBasedStateMachine):
        a = Bundle("a")
        b = Bundle("b")

        @initialize(targets=(a, b, a))
        def initialize(self):
            return multiple("ret1", "ret2", "ret3")

        @rule(
            a1=consumes(a),
            a2=consumes(a),
            a3=consumes(a),
            a4=consumes(a),
            a5=consumes(a),
            a6=consumes(a),
            b1=consumes(b),
            b2=consumes(b),
            b3=consumes(b),
        )
        def fail_fast(self, a1, a2, a3, a4, a5, a6, b1, b2, b3):
            raise AssertionError

    Machine.TestCase.settings = NO_BLOB_SETTINGS
    with pytest.raises(AssertionError) as err:
        run_state_machine_as_test(Machine)

    result = "\n".join(err.value.__notes__)
    assert (
        result
        == """
Falsifying example:
state = Machine()
a_0, a_1, a_2 = state.initialize()
b_0, b_1, b_2 = a_0, a_1, a_2
a_3, a_4, a_5 = a_0, a_1, a_2
state.fail_fast(a1=a_5, a2=a_4, a3=a_3, a4=a_2, a5=a_1, a6=a_0, b1=b_2, b2=b_1, b3=b_0)
state.teardown()
""".strip()
    )


class LotsOfEntropyPerStepMachine(RuleBasedStateMachine):
    # Regression tests for https://github.com/HypothesisWorks/hypothesis/issues/3618
    @rule(data=binary(min_size=512, max_size=512))
    def rule1(self, data):
        assert data


@pytest.mark.skipif(
    Settings._current_profile == "crosshair",
    reason="takes hours; too much symbolic data",
)
def test_lots_of_entropy():
    run_state_machine_as_test(LotsOfEntropyPerStepMachine)


def test_flatmap():
    class Machine(RuleBasedStateMachine):
        buns = Bundle("buns")

        @initialize(target=buns)
        def create_bun(self):
            return 0

        @rule(target=buns, bun=buns.flatmap(lambda x: just(x + 1)))
        def use_flatmap(self, bun):
            assert isinstance(bun, int)
            return bun

        @rule(bun=buns)
        def use_directly(self, bun):
            assert isinstance(bun, int)

    Machine.TestCase.settings = Settings(stateful_step_count=5, max_examples=10)
    run_state_machine_as_test(Machine)


def test_use_bundle_within_other_strategies():
    class Class:
        def __init__(self, value):
            self.value = value

    class Machine(RuleBasedStateMachine):
        my_bundle = Bundle("my_bundle")

        @initialize(target=my_bundle)
        def set_initial(self, /) -> str:
            return "sample text"

        @rule(instance=st.builds(Class, my_bundle))
        def check(self, instance):
            assert isinstance(instance, Class)
            assert isinstance(instance.value, str)

    Machine.TestCase.settings = Settings(stateful_step_count=5, max_examples=10)
    run_state_machine_as_test(Machine)
