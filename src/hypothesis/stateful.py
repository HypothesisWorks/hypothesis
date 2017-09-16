# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

"""This module provides support for a stateful style of testing, where tests
attempt to find a sequence of operations that cause a breakage rather than just
a single value.

Notably, the set of steps available at any point may depend on the
execution to date.

"""


from __future__ import division, print_function, absolute_import

import inspect
import traceback
from unittest import TestCase

import attr

import hypothesis.internal.conjecture.utils as cu
from hypothesis.core import find
from hypothesis.errors import Flaky, NoSuchExample, InvalidDefinition, \
    HypothesisException
from hypothesis.control import BuildContext
from hypothesis._settings import settings as Settings
from hypothesis._settings import Verbosity
from hypothesis.reporting import report, verbose_report, current_verbosity
from hypothesis.strategies import just, lists, builds, one_of, runner, \
    integers
from hypothesis.vendor.pretty import CUnicodeIO, RepresentationPrinter
from hypothesis.internal.reflection import proxies, nicerepr
from hypothesis.internal.conjecture.data import StopTest
from hypothesis.internal.conjecture.utils import integer_range
from hypothesis.searchstrategy.strategies import SearchStrategy
from hypothesis.searchstrategy.collections import TupleStrategy, \
    FixedKeysDictStrategy


class TestCaseProperty(object):  # pragma: no cover

    def __get__(self, obj, typ=None):
        if obj is not None:
            typ = type(obj)
        return typ._to_test_case()

    def __set__(self, obj, value):
        raise AttributeError(u'Cannot set TestCase')

    def __delete__(self, obj):
        raise AttributeError(u'Cannot delete TestCase')


def find_breaking_runner(state_machine_factory, settings=None):
    def is_breaking_run(runner):
        try:
            runner.run(state_machine_factory())
            return False
        except HypothesisException:
            raise
        except Exception:
            verbose_report(traceback.format_exc)
            return True
    if settings is None:
        try:
            settings = state_machine_factory.TestCase.settings
        except AttributeError:
            settings = Settings.default

    search_strategy = StateMachineSearchStrategy(settings)

    return find(
        search_strategy,
        is_breaking_run,
        settings=settings,
        database_key=state_machine_factory.__name__.encode('utf-8')
    )


def run_state_machine_as_test(state_machine_factory, settings=None):
    """Run a state machine definition as a test, either silently doing nothing
    or printing a minimal breaking program and raising an exception.

    state_machine_factory is anything which returns an instance of
    GenericStateMachine when called with no arguments - it can be a class or a
    function. settings will be used to control the execution of the test.

    """
    try:
        breaker = find_breaking_runner(state_machine_factory, settings)
    except NoSuchExample:
        return
    try:
        with BuildContext(None, is_final=True):
            breaker.run(state_machine_factory(), print_steps=True)
    except StopTest:
        pass
    raise Flaky(
        u'Run failed initially but succeeded on a second try'
    )


class GenericStateMachine(object):

    """A GenericStateMachine is the basic entry point into Hypothesis's
    approach to stateful testing.

    The intent is for it to be subclassed to provide state machine descriptions

    The way this is used is that Hypothesis will repeatedly execute something
    that looks something like::

        x = MyStatemachineSubclass()
        x.check_invariants()
        try:
            for _ in range(n_steps):
                x.execute_step(x.steps().example())
                x.check_invariants()
        finally:
            x.teardown()

    And if this ever produces an error it will shrink it down to a small
    sequence of example choices demonstrating that.

    """

    def steps(self):
        """Return a SearchStrategy instance the defines the available next
        steps."""
        raise NotImplementedError(u'%r.steps()' % (self,))

    def execute_step(self, step):
        """Execute a step that has been previously drawn from self.steps()"""
        raise NotImplementedError(u'%r.execute_step()' % (self,))

    def print_step(self, step):
        """Print a step to the current reporter.

        This is called right before a step is executed.

        """
        self.step_count = getattr(self, u'step_count', 0) + 1
        report(u'Step #%d: %s' % (self.step_count, nicerepr(step)))

    def teardown(self):
        """Called after a run has finished executing to clean up any necessary
        state.

        Does nothing by default

        """
        pass

    def check_invariants(self):
        """Called after initializing and after executing each step."""
        pass

    _test_case_cache = {}

    TestCase = TestCaseProperty()

    @classmethod
    def _to_test_case(state_machine_class):
        try:
            return state_machine_class._test_case_cache[state_machine_class]
        except KeyError:
            pass

        class StateMachineTestCase(TestCase):
            settings = Settings(
                min_satisfying_examples=1
            )

        # We define this outside of the class and assign it because you can't
        # assign attributes to instance method values in Python 2
        def runTest(self):
            run_state_machine_as_test(state_machine_class)

        runTest.is_hypothesis_test = True
        StateMachineTestCase.runTest = runTest
        base_name = state_machine_class.__name__
        StateMachineTestCase.__name__ = str(
            base_name + u'.TestCase'
        )
        StateMachineTestCase.__qualname__ = str(
            getattr(state_machine_class, u'__qualname__', base_name) +
            u'.TestCase'
        )
        state_machine_class._test_case_cache[state_machine_class] = (
            StateMachineTestCase
        )
        return StateMachineTestCase


GenericStateMachine.find_breaking_runner = classmethod(find_breaking_runner)


class StateMachineRunner(object):

    """A StateMachineRunner is a description of how to run a state machine.

    It contains values that it will use to shape the examples.

    """

    def __init__(self, data, n_steps):
        self.data = data
        self.data.is_find = False
        self.n_steps = n_steps

    def run(self, state_machine, print_steps=None):
        if print_steps is None:
            print_steps = current_verbosity() >= Verbosity.debug
        self.data.hypothesis_runner = state_machine

        stopping_value = 1 - 1.0 / (1 + self.n_steps * 0.5)
        try:
            state_machine.check_invariants()

            steps = 0
            while True:
                if steps >= self.n_steps:
                    stopping_value = 0
                self.data.start_example()
                if not cu.biased_coin(self.data, stopping_value):
                    self.data.stop_example()
                    break
                assert steps < self.n_steps
                value = self.data.draw(state_machine.steps())
                steps += 1
                if print_steps:
                    state_machine.print_step(value)
                state_machine.execute_step(value)
                self.data.stop_example()
                state_machine.check_invariants()
        finally:
            state_machine.teardown()


class StateMachineSearchStrategy(SearchStrategy):

    def __init__(self, settings=None):
        self.program_size = (settings or Settings.default).stateful_step_count

    def do_draw(self, data):
        return StateMachineRunner(data, self.program_size)


@attr.s()
class Rule(object):
    targets = attr.ib()
    function = attr.ib()
    arguments = attr.ib()
    precondition = attr.ib()


self_strategy = runner()


class Bundle(SearchStrategy):

    def __init__(self, name):
        self.name = name

    def do_draw(self, data):
        machine = data.draw(self_strategy)
        bundle = machine.bundle(self.name)
        if not bundle:
            data.mark_invalid()
        reference = bundle.pop()
        bundle.insert(integer_range(data, 0, len(bundle)), reference)
        return machine.names_to_values[reference.name]


RULE_MARKER = u'hypothesis_stateful_rule'
PRECONDITION_MARKER = u'hypothesis_stateful_precondition'
INVARIANT_MARKER = u'hypothesis_stateful_invariant'


def rule(targets=(), target=None, **kwargs):
    """Decorator for RuleBasedStateMachine. Any name present in target or
    targets will define where the end result of this function should go. If
    both are empty then the end result will be discarded.

    targets may either be a Bundle or the name of a Bundle.

    kwargs then define the arguments that will be passed to the function
    invocation. If their value is a Bundle then values that have previously
    been produced for that bundle will be provided, if they are anything else
    it will be turned into a strategy and values from that will be provided.

    """
    if target is not None:
        targets += (target,)

    converted_targets = []
    for t in targets:
        while isinstance(t, Bundle):
            t = t.name
        converted_targets.append(t)

    def accept(f):
        existing_rule = getattr(f, RULE_MARKER, None)
        if existing_rule is not None:
            raise InvalidDefinition(
                'A function cannot be used for two distinct rules. ',
                Settings.default,
            )
        precondition = getattr(f, PRECONDITION_MARKER, None)
        rule = Rule(targets=tuple(converted_targets), arguments=kwargs,
                    function=f, precondition=precondition)

        @proxies(f)
        def rule_wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        setattr(rule_wrapper, RULE_MARKER, rule)
        return rule_wrapper
    return accept


@attr.s()
class VarReference(object):
    name = attr.ib()


def precondition(precond):
    """Decorator to apply a precondition for rules in a RuleBasedStateMachine.
    Specifies a precondition for a rule to be considered as a valid step in the
    state machine. The given function will be called with the instance of
    RuleBasedStateMachine and should return True or False. Usually it will need
    to look at attributes on that instance.

    For example::

        class MyTestMachine(RuleBasedStateMachine):
            state = 1

            @precondition(lambda self: self.state != 0)
            @rule(numerator=integers())
            def divide_with(self, numerator):
                self.state = numerator / self.state

    This is better than using assume in your rule since more valid rules
    should be able to be run.

    """
    def decorator(f):
        @proxies(f)
        def precondition_wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        rule = getattr(f, RULE_MARKER, None)
        if rule is None:
            setattr(precondition_wrapper, PRECONDITION_MARKER, precond)
        else:
            new_rule = Rule(targets=rule.targets, arguments=rule.arguments,
                            function=rule.function, precondition=precond)
            setattr(precondition_wrapper, RULE_MARKER, new_rule)

        invariant = getattr(f, INVARIANT_MARKER, None)
        if invariant is not None:
            new_invariant = Invariant(function=invariant.function,
                                      precondition=precond)
            setattr(precondition_wrapper, INVARIANT_MARKER, new_invariant)

        return precondition_wrapper
    return decorator


@attr.s()
class Invariant(object):
    function = attr.ib()
    precondition = attr.ib()


def invariant():
    """Decorator to apply an invariant for rules in a RuleBasedStateMachine.
    The decorated function will be run after every rule and can raise an
    exception to indicate failed invariants.

    For example::

        class MyTestMachine(RuleBasedStateMachine):
            state = 1

            @invariant()
            def is_nonzero(self):
                assert self.state != 0

    """
    def accept(f):
        existing_invariant = getattr(f, INVARIANT_MARKER, None)
        if existing_invariant is not None:
            raise InvalidDefinition(
                'A function cannot be used for two distinct invariants.',
                Settings.default,
            )
        precondition = getattr(f, PRECONDITION_MARKER, None)
        rule = Invariant(function=f, precondition=precondition)

        @proxies(f)
        def invariant_wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        setattr(invariant_wrapper, INVARIANT_MARKER, rule)
        return invariant_wrapper
    return accept


@attr.s()
class ShuffleBundle(object):
    bundle = attr.ib()
    swaps = attr.ib()


class RuleBasedStateMachine(GenericStateMachine):

    """A RuleBasedStateMachine gives you a more structured way to define state
    machines.

    The idea is that a state machine carries a bunch of types of data
    divided into Bundles, and has a set of rules which may read data
    from bundles (or just from normal strategies) and push data onto
    bundles. At any given point a random applicable rule will be
    executed.

    """
    _rules_per_class = {}
    _invariants_per_class = {}
    _base_rules_per_class = {}

    def __init__(self):
        if not self.rules():
            raise InvalidDefinition(u'Type %s defines no rules' % (
                type(self).__name__,
            ))
        self.bundles = {}
        self.name_counter = 1
        self.names_to_values = {}
        self.__stream = CUnicodeIO()
        self.__printer = RepresentationPrinter(self.__stream)

    def __pretty(self, value):
        self.__stream.seek(0)
        self.__stream.truncate(0)
        self.__printer.output_width = 0
        self.__printer.buffer_width = 0
        self.__printer.buffer.clear()
        self.__printer.pretty(value)
        self.__printer.flush()
        return self.__stream.getvalue()

    def __repr__(self):
        return u'%s(%s)' % (
            type(self).__name__,
            nicerepr(self.bundles),
        )

    def upcoming_name(self):
        return u'v%d' % (self.name_counter,)

    def new_name(self):
        result = self.upcoming_name()
        self.name_counter += 1
        return result

    def bundle(self, name):
        return self.bundles.setdefault(name, [])

    @classmethod
    def rules(cls):
        try:
            return cls._rules_per_class[cls]
        except KeyError:
            pass

        for k, v in inspect.getmembers(cls):
            r = getattr(v, RULE_MARKER, None)
            if r is not None:
                cls.define_rule(
                    r.targets, r.function, r.arguments, r.precondition,
                )
        cls._rules_per_class[cls] = cls._base_rules_per_class.pop(cls, [])
        return cls._rules_per_class[cls]

    @classmethod
    def invariants(cls):
        try:
            return cls._invariants_per_class[cls]
        except KeyError:
            pass

        target = []
        for k, v in inspect.getmembers(cls):
            i = getattr(v, INVARIANT_MARKER, None)
            if i is not None:
                target.append(i)
        cls._invariants_per_class[cls] = target
        return cls._invariants_per_class[cls]

    @classmethod
    def define_rule(cls, targets, function, arguments, precondition=None):
        converted_arguments = {}
        for k, v in arguments.items():
            converted_arguments[k] = v
        if cls in cls._rules_per_class:
            target = cls._rules_per_class[cls]
        else:
            target = cls._base_rules_per_class.setdefault(cls, [])

        return target.append(
            Rule(
                targets, function, converted_arguments, precondition,
            )
        )

    def steps(self):
        strategies = []
        for rule in self.rules():
            converted_arguments = {}
            valid = True
            if rule.precondition and not rule.precondition(self):
                continue
            for k, v in sorted(rule.arguments.items()):
                if isinstance(v, Bundle):
                    bundle = self.bundle(v.name)
                    if not bundle:
                        valid = False
                        break
                converted_arguments[k] = v
            if valid:
                strategies.append(TupleStrategy((
                    just(rule),
                    FixedKeysDictStrategy(converted_arguments)
                ), tuple))
        if not strategies:
            raise InvalidDefinition(
                u'No progress can be made from state %r' % (self,)
            )

        for name, bundle in self.bundles.items():
            if len(bundle) > 1:
                strategies.append(
                    builds(
                        ShuffleBundle, just(name),
                        lists(integers(0, len(bundle) - 1))))

        return one_of(strategies)

    def print_step(self, step):
        if isinstance(step, ShuffleBundle):
            return
        rule, data = step
        data_repr = {}
        for k, v in data.items():
            data_repr[k] = self.__pretty(v)
        self.step_count = getattr(self, u'step_count', 0) + 1
        report(u'Step #%d: %s%s(%s)' % (
            self.step_count,
            u'%s = ' % (self.upcoming_name(),) if rule.targets else u'',
            rule.function.__name__,
            u', '.join(u'%s=%s' % kv for kv in data_repr.items())
        ))

    def execute_step(self, step):
        if isinstance(step, ShuffleBundle):
            bundle = self.bundle(step.bundle)
            for i in step.swaps:
                bundle.insert(i, bundle.pop())
            return
        rule, data = step
        data = dict(data)
        result = rule.function(self, **data)
        if rule.targets:
            name = self.new_name()
            self.names_to_values[name] = result
            self.__printer.singleton_pprinters.setdefault(
                id(result), lambda obj, p, cycle: p.text(name),
            )
            for target in rule.targets:
                self.bundle(target).append(VarReference(name))

    def check_invariants(self):
        for invar in self.invariants():
            if invar.precondition and not invar.precondition(self):
                continue
            invar.function(self)
