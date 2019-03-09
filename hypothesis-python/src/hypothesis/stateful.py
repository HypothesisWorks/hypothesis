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

"""This module provides support for a stateful style of testing, where tests
attempt to find a sequence of operations that cause a breakage rather than just
a single value.

Notably, the set of steps available at any point may depend on the
execution to date.
"""


from __future__ import absolute_import, division, print_function

import inspect
from copy import copy
from unittest import TestCase

import attr

import hypothesis.internal.conjecture.utils as cu
import hypothesis.strategies as st
from hypothesis._settings import (
    HealthCheck,
    Verbosity,
    note_deprecation,
    settings as Settings,
)
from hypothesis.control import current_build_context
from hypothesis.core import given
from hypothesis.errors import InvalidArgument, InvalidDefinition
from hypothesis.internal.compat import string_types
from hypothesis.internal.reflection import function_digest, nicerepr, proxies
from hypothesis.internal.validation import check_type
from hypothesis.reporting import current_verbosity, report
from hypothesis.searchstrategy.strategies import OneOfStrategy, SearchStrategy
from hypothesis.vendor.pretty import CUnicodeIO, RepresentationPrinter

STATE_MACHINE_RUN_LABEL = cu.calc_label_from_name("another state machine step")

if False:
    from typing import Any, Dict, List, Text  # noqa


class TestCaseProperty(object):  # pragma: no cover
    def __get__(self, obj, typ=None):
        if obj is not None:
            typ = type(obj)
        return typ._to_test_case()

    def __set__(self, obj, value):
        raise AttributeError(u"Cannot set TestCase")

    def __delete__(self, obj):
        raise AttributeError(u"Cannot delete TestCase")


def run_state_machine_as_test(state_machine_factory, settings=None):
    """Run a state machine definition as a test, either silently doing nothing
    or printing a minimal breaking program and raising an exception.

    state_machine_factory is anything which returns an instance of
    GenericStateMachine when called with no arguments - it can be a class or a
    function. settings will be used to control the execution of the test.
    """
    if settings is None:
        try:
            settings = state_machine_factory.TestCase.settings
            check_type(Settings, settings, "state_machine_factory.TestCase.settings")
        except AttributeError:
            settings = Settings(deadline=None, suppress_health_check=HealthCheck.all())
    check_type(Settings, settings, "settings")

    @settings
    @given(st.data())
    def run_state_machine(factory, data):
        machine = factory()
        check_type(GenericStateMachine, machine, "state_machine_factory()")
        data.conjecture_data.hypothesis_runner = machine

        n_steps = settings.stateful_step_count
        should_continue = cu.many(
            data.conjecture_data, min_size=1, max_size=n_steps, average_size=n_steps
        )

        print_steps = (
            current_build_context().is_final or current_verbosity() >= Verbosity.debug
        )
        try:
            if print_steps:
                machine.print_start()
            machine.check_invariants()

            while should_continue.more():
                value = data.conjecture_data.draw(machine.steps())
                if print_steps:
                    machine.print_step(value)
                machine.execute_step(value)
                machine.check_invariants()
        finally:
            if print_steps:
                machine.print_end()
            machine.teardown()

    # Use a machine digest to identify stateful tests in the example database
    run_state_machine.hypothesis.inner_test._hypothesis_internal_add_digest = function_digest(
        state_machine_factory
    )
    # Copy some attributes so @seed and @reproduce_failure "just work"
    run_state_machine._hypothesis_internal_use_seed = getattr(
        state_machine_factory, "_hypothesis_internal_use_seed", None
    )
    run_state_machine._hypothesis_internal_use_reproduce_failure = getattr(
        state_machine_factory, "_hypothesis_internal_use_reproduce_failure", None
    )

    run_state_machine(state_machine_factory)


class GenericStateMachineMeta(type):
    def __init__(self, *args, **kwargs):
        super(GenericStateMachineMeta, self).__init__(*args, **kwargs)

    def __setattr__(self, name, value):
        if name == "settings" and isinstance(value, Settings):
            raise AttributeError(
                (
                    "Assigning {cls}.settings = {value} does nothing. Assign "
                    "to {cls}.TestCase.settings, or use @{value} as a decorator "
                    "on the {cls} class."
                ).format(cls=self.__name__, value=value)
            )
        return type.__setattr__(self, name, value)


class GenericStateMachine(
    GenericStateMachineMeta("GenericStateMachine", (object,), {})  # type: ignore
):
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
        raise NotImplementedError(u"%r.steps()" % (self,))

    def execute_step(self, step):
        """Execute a step that has been previously drawn from self.steps()"""
        raise NotImplementedError(u"%r.execute_step()" % (self,))

    def print_start(self):
        """Called right at the start of printing.

        By default does nothing.
        """

    def print_end(self):
        """Called right at the end of printing.

        By default does nothing.
        """

    def print_step(self, step):
        """Print a step to the current reporter.

        This is called right before a step is executed.
        """
        self.step_count = getattr(self, u"step_count", 0) + 1
        report(u"Step #%d: %s" % (self.step_count, nicerepr(step)))

    def teardown(self):
        """Called after a run has finished executing to clean up any necessary
        state.

        Does nothing by default.
        """
        pass

    def check_invariants(self):
        """Called after initializing and after executing each step."""
        pass

    _test_case_cache = {}  # type: dict

    TestCase = TestCaseProperty()

    @classmethod
    def _to_test_case(state_machine_class):
        try:
            return state_machine_class._test_case_cache[state_machine_class]
        except KeyError:
            pass

        class StateMachineTestCase(TestCase):
            settings = Settings(deadline=None, suppress_health_check=HealthCheck.all())

        # We define this outside of the class and assign it because you can't
        # assign attributes to instance method values in Python 2
        def runTest(self):
            run_state_machine_as_test(state_machine_class)

        runTest.is_hypothesis_test = True
        StateMachineTestCase.runTest = runTest
        base_name = state_machine_class.__name__
        StateMachineTestCase.__name__ = str(base_name + u".TestCase")
        StateMachineTestCase.__qualname__ = str(
            getattr(state_machine_class, u"__qualname__", base_name) + u".TestCase"
        )
        state_machine_class._test_case_cache[state_machine_class] = StateMachineTestCase
        return StateMachineTestCase


@attr.s()
class Rule(object):
    targets = attr.ib()
    function = attr.ib()
    arguments = attr.ib()
    precondition = attr.ib()
    bundles = attr.ib(init=False)

    def __attrs_post_init__(self):
        arguments = {}
        bundles = []
        for k, v in sorted(self.arguments.items()):
            assert not isinstance(v, BundleReferenceStrategy)
            if isinstance(v, Bundle):
                bundles.append(v)
                consume = isinstance(v, BundleConsumer)
                arguments[k] = BundleReferenceStrategy(v.name, consume)
            else:
                arguments[k] = v
        self.bundles = tuple(bundles)
        self.arguments_strategy = st.fixed_dictionaries(arguments)


self_strategy = st.runner()


class BundleReferenceStrategy(SearchStrategy):
    def __init__(self, name, consume=False):
        self.name = name
        self.consume = consume

    def do_draw(self, data):
        machine = data.draw(self_strategy)
        bundle = machine.bundle(self.name)
        if not bundle:
            data.mark_invalid()
        # Shrink towards the right rather than the left. This makes it easier
        # to delete data generated earlier, as when the error is towards the
        # end there can be a lot of hard to remove padding.
        position = cu.integer_range(data, 0, len(bundle) - 1, center=len(bundle))
        if self.consume:
            return bundle.pop(position)
        else:
            return bundle[position]


class Bundle(SearchStrategy):
    def __init__(self, name, consume=False):
        self.name = name
        self.__reference_strategy = BundleReferenceStrategy(name, consume)

    def do_draw(self, data):
        machine = data.draw(self_strategy)
        reference = data.draw(self.__reference_strategy)
        return machine.names_to_values[reference.name]


class BundleConsumer(Bundle):
    def __init__(self, bundle):
        super(BundleConsumer, self).__init__(bundle.name, consume=True)


def consumes(bundle):
    """When introducing a rule in a RuleBasedStateMachine, this function can
    be used to mark bundles from which each value used in a step with the
    given rule should be removed. This function returns a strategy object
    that can be manipulated and combined like any other.

    For example, a rule declared with

    ``@rule(value1=b1, value2=consumes(b2), value3=lists(consumes(b3)))``

    will consume a value from Bundle ``b2`` and several values from Bundle
    ``b3`` to populate ``value2`` and ``value3`` each time it is executed.
    """
    if not isinstance(bundle, Bundle):
        raise TypeError("Argument to be consumed must be a bundle.")
    return BundleConsumer(bundle)


@attr.s()
class MultipleResults(object):
    values = attr.ib()


def multiple(*args):
    """This function can be used to pass multiple results to the target(s) of
    a rule. Just use ``return multiple(result1, result2, ...)`` in your rule.

    It is also possible to use ``return multiple()`` with no arguments in
    order to end a rule without passing any result.
    """
    return MultipleResults(args)


def _convert_targets(targets, target):
    """Single validator and convertor for target arguments."""
    if target is not None:
        if targets:
            note_deprecation(
                "Passing both targets=%r and target=%r is redundant, and "
                "will become an error in a future version of Hypothesis.  "
                "Pass targets=%r instead."
                % (targets, target, tuple(targets) + (target,)),
                since="2018-08-18",
            )
        targets = tuple(targets) + (target,)

    converted_targets = []
    for t in targets:
        if isinstance(t, string_types):
            note_deprecation(
                "Got %r as a target, but passing the name of a Bundle is "
                "deprecated - please pass the Bundle directly." % (t,),
                since="2018-08-18",
            )
        elif not isinstance(t, Bundle):
            msg = (
                "Got invalid target %r of type %r, but all targets must "
                "be either a Bundle or the name of a Bundle."
            )
            if isinstance(t, OneOfStrategy):
                msg += (
                    "\nIt looks like you passed `one_of(a, b)` or `a | b` as "
                    "a target.  You should instead pass `targets=(a, b)` to "
                    "add the return value of this rule to both the `a` and "
                    "`b` bundles, or define a rule for each target if it "
                    "should be added to exactly one."
                )
            raise InvalidArgument(msg % (t, type(t)))
        while isinstance(t, Bundle):
            t = t.name
        converted_targets.append(t)
    return tuple(converted_targets)


RULE_MARKER = u"hypothesis_stateful_rule"
INITIALIZE_RULE_MARKER = u"hypothesis_stateful_initialize_rule"
PRECONDITION_MARKER = u"hypothesis_stateful_precondition"
INVARIANT_MARKER = u"hypothesis_stateful_invariant"


def rule(targets=(), target=None, **kwargs):
    """Decorator for RuleBasedStateMachine. Any name present in target or
    targets will define where the end result of this function should go. If
    both are empty then the end result will be discarded.

    ``target`` must be a Bundle, or if the result should go to multiple
    bundles you can pass a tuple of them as the ``targets`` argument.
    It is invalid to use both arguments for a single rule.  If the result
    should go to exactly one of several bundles, define a separate rule for
    each case.

    kwargs then define the arguments that will be passed to the function
    invocation. If their value is a Bundle, or if it is ``consumes(b)``
    where ``b`` is a Bundle, then values that have previously been produced
    for that bundle will be provided. If ``consumes`` is used, the value
    will also be removed from the bundle.

    Any other kwargs should be strategies and values from them will be
    provided.
    """
    converted_targets = _convert_targets(targets, target)

    def accept(f):
        existing_rule = getattr(f, RULE_MARKER, None)
        existing_initialize_rule = getattr(f, INITIALIZE_RULE_MARKER, None)
        if existing_rule is not None or existing_initialize_rule is not None:
            raise InvalidDefinition(
                "A function cannot be used for two distinct rules. ", Settings.default
            )
        precondition = getattr(f, PRECONDITION_MARKER, None)
        rule = Rule(
            targets=converted_targets,
            arguments=kwargs,
            function=f,
            precondition=precondition,
        )

        @proxies(f)
        def rule_wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        setattr(rule_wrapper, RULE_MARKER, rule)
        return rule_wrapper

    return accept


def initialize(targets=(), target=None, **kwargs):
    """Decorator for RuleBasedStateMachine.

    An initialize decorator behaves like a rule, but the decorated
    method is called at most once in a run. All initialize decorated
    methods will be called before any rule decorated methods, in an
    arbitrary order.
    """
    converted_targets = _convert_targets(targets, target)

    def accept(f):
        existing_rule = getattr(f, RULE_MARKER, None)
        existing_initialize_rule = getattr(f, INITIALIZE_RULE_MARKER, None)
        if existing_rule is not None or existing_initialize_rule is not None:
            raise InvalidDefinition(
                "A function cannot be used for two distinct rules. ", Settings.default
            )
        precondition = getattr(f, PRECONDITION_MARKER, None)
        if precondition:
            raise InvalidDefinition(
                "An initialization rule cannot have a precondition. ", Settings.default
            )
        rule = Rule(
            targets=converted_targets,
            arguments=kwargs,
            function=f,
            precondition=precondition,
        )

        @proxies(f)
        def rule_wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        setattr(rule_wrapper, INITIALIZE_RULE_MARKER, rule)
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

        existing_initialize_rule = getattr(f, INITIALIZE_RULE_MARKER, None)
        if existing_initialize_rule is not None:
            raise InvalidDefinition(
                "An initialization rule cannot have a precondition. ", Settings.default
            )

        rule = getattr(f, RULE_MARKER, None)
        if rule is None:
            setattr(precondition_wrapper, PRECONDITION_MARKER, precond)
        else:
            new_rule = Rule(
                targets=rule.targets,
                arguments=rule.arguments,
                function=rule.function,
                precondition=precond,
            )
            setattr(precondition_wrapper, RULE_MARKER, new_rule)

        invariant = getattr(f, INVARIANT_MARKER, None)
        if invariant is not None:
            new_invariant = Invariant(function=invariant.function, precondition=precond)
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
                "A function cannot be used for two distinct invariants.",
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


LOOP_LABEL = cu.calc_label_from_name("RuleStrategy loop iteration")


class RuleStrategy(SearchStrategy):
    def __init__(self, machine):
        SearchStrategy.__init__(self)
        self.machine = machine
        self.rules = list(machine.rules())

        # The order is a bit arbitrary. Primarily we're trying to group rules
        # that write to the same location together, and to put rules with no
        # target first as they have less effect on the structure. We order from
        # fewer to more arguments on grounds that it will plausibly need less
        # data. This probably won't work especially well and we could be
        # smarter about it, but it's better than just doing it in definition
        # order.
        self.rules.sort(
            key=lambda rule: (
                sorted(rule.targets),
                len(rule.arguments),
                rule.function.__name__,
            )
        )

    def do_draw(self, data):
        # This strategy is slightly strange in its implementation.
        # We don't want the interpretation of the rule we draw to change based
        # on whether other rules satisfy their preconditions or have data in
        # their bundles. Therefore the index into the rule list needs to stay
        # stable. BUT we don't want to draw invalid rules. So what we do is we
        # draw an index. We *could* just loop until it's valid, but if most
        # rules are invalid then that could result in a very long loop.
        # So what we do is the following:
        #
        #   1. We first draw a rule unconditionally, and check if it's valid.
        #      If it is, great. Nothing more to do, that's our rule.
        #   2. If it is invalid, we now calculate the list of valid rules and
        #      draw from that list (if there are none, that's an error in the
        #      definition of the machine and we complain to the user about it).
        #   3. Once we've drawn a valid rule, we write that back to the byte
        #      stream. As a result, when shrinking runs the shrinker can delete
        #      the initial failed draw + the draw that lead to us finding an
        #      index into valid_rules, leaving just the written value of i.
        #      When this is run, it will look as we got lucky and just happened
        #      to pick a valid rule.
        #
        # Easy, right?
        n = len(self.rules)
        i = cu.integer_range(data, 0, n - 1)
        block_length = data.blocks.last_block_length
        rule = self.rules[i]
        if not self.is_valid(rule):
            valid_rules = [j for j, r in enumerate(self.rules) if self.is_valid(r)]
            if not valid_rules:
                raise InvalidDefinition(
                    u"No progress can be made from state %r" % (self.machine,)
                )
            i = valid_rules[cu.integer_range(data, 0, len(valid_rules) - 1)]
            # Insert a copy of ``i`` into the data stream to make it easier for
            # the shrinker to delete the initial invalid rule draw.
            data.draw_bits(block_length * 8, forced=i)
            rule = self.rules[i]
        return (rule, data.draw(rule.arguments_strategy))

    def is_valid(self, rule):
        if rule.precondition and not rule.precondition(self.machine):
            return False
        for b in rule.bundles:
            bundle = self.machine.bundle(b.name)
            if not bundle:
                return False
        return True


class RuleBasedStateMachine(GenericStateMachine):
    """A RuleBasedStateMachine gives you a more structured way to define state
    machines.

    The idea is that a state machine carries a bunch of types of data
    divided into Bundles, and has a set of rules which may read data
    from bundles (or just from normal strategies) and push data onto
    bundles. At any given point a random applicable rule will be
    executed.
    """

    _rules_per_class = {}  # type: Dict[type, List[classmethod]]
    _invariants_per_class = {}  # type: Dict[type, List[classmethod]]
    _base_rules_per_class = {}  # type: Dict[type, List[classmethod]]
    _initializers_per_class = {}  # type: Dict[type, List[classmethod]]
    _base_initializers_per_class = {}  # type: Dict[type, List[classmethod]]

    def __init__(self):
        if not self.rules():
            raise InvalidDefinition(
                u"Type %s defines no rules" % (type(self).__name__,)
            )
        self.bundles = {}  # type: Dict[Text, list]
        self.name_counter = 1
        self.names_to_values = {}  # type: Dict[Text, Any]
        self.__stream = CUnicodeIO()
        self.__printer = RepresentationPrinter(self.__stream)
        self._initialize_rules_to_run = copy(self.initialize_rules())
        self.__rules_strategy = RuleStrategy(self)

    def __pretty(self, value):
        if isinstance(value, VarReference):
            return value.name
        self.__stream.seek(0)
        self.__stream.truncate(0)
        self.__printer.output_width = 0
        self.__printer.buffer_width = 0
        self.__printer.buffer.clear()
        self.__printer.pretty(value)
        self.__printer.flush()
        return self.__stream.getvalue()

    def __repr__(self):
        return u"%s(%s)" % (type(self).__name__, nicerepr(self.bundles))

    def upcoming_name(self):
        return u"v%d" % (self.name_counter,)

    def new_name(self):
        result = self.upcoming_name()
        self.name_counter += 1
        return result

    def bundle(self, name):
        return self.bundles.setdefault(name, [])

    @classmethod
    def initialize_rules(cls):
        try:
            return cls._initializers_per_class[cls]
        except KeyError:
            pass

        for k, v in inspect.getmembers(cls):
            r = getattr(v, INITIALIZE_RULE_MARKER, None)
            if r is not None:
                cls.define_initialize_rule(
                    r.targets, r.function, r.arguments, r.precondition
                )
        cls._initializers_per_class[cls] = cls._base_initializers_per_class.pop(cls, [])
        return cls._initializers_per_class[cls]

    @classmethod
    def rules(cls):
        try:
            return cls._rules_per_class[cls]
        except KeyError:
            pass

        for k, v in inspect.getmembers(cls):
            r = getattr(v, RULE_MARKER, None)
            if r is not None:
                cls.define_rule(r.targets, r.function, r.arguments, r.precondition)
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
    def define_initialize_rule(cls, targets, function, arguments, precondition=None):
        converted_arguments = {}
        for k, v in arguments.items():
            converted_arguments[k] = v
        if cls in cls._initializers_per_class:
            target = cls._initializers_per_class[cls]
        else:
            target = cls._base_initializers_per_class.setdefault(cls, [])

        return target.append(Rule(targets, function, converted_arguments, precondition))

    @classmethod
    def define_rule(cls, targets, function, arguments, precondition=None):
        converted_arguments = {}
        for k, v in arguments.items():
            converted_arguments[k] = v
        if cls in cls._rules_per_class:
            target = cls._rules_per_class[cls]
        else:
            target = cls._base_rules_per_class.setdefault(cls, [])

        return target.append(Rule(targets, function, converted_arguments, precondition))

    def steps(self):
        # Pick initialize rules first
        if self._initialize_rules_to_run:
            return st.one_of(
                [
                    st.tuples(st.just(rule), st.fixed_dictionaries(rule.arguments))
                    for rule in self._initialize_rules_to_run
                ]
            )

        return self.__rules_strategy

    def print_start(self):
        report(u"state = %s()" % (self.__class__.__name__,))

    def print_end(self):
        report(u"state.teardown()")

    def print_step(self, step):
        rule, data = step
        data_repr = {}
        for k, v in data.items():
            data_repr[k] = self.__pretty(v)
        self.step_count = getattr(self, u"step_count", 0) + 1
        report(
            u"%sstate.%s(%s)"
            % (
                u"%s = " % (self.upcoming_name(),) if rule.targets else u"",
                rule.function.__name__,
                u", ".join(u"%s=%s" % kv for kv in data_repr.items()),
            )
        )

    def _add_result_to_targets(self, targets, result):
        name = self.new_name()
        self.__printer.singleton_pprinters.setdefault(
            id(result), lambda obj, p, cycle: p.text(name)
        )
        self.names_to_values[name] = result
        for target in targets:
            self.bundle(target).append(VarReference(name))

    def execute_step(self, step):
        rule, data = step
        data = dict(data)
        for k, v in list(data.items()):
            if isinstance(v, VarReference):
                data[k] = self.names_to_values[v.name]
        result = rule.function(self, **data)
        if rule.targets:
            if isinstance(result, MultipleResults):
                for single_result in result.values:
                    self._add_result_to_targets(rule.targets, single_result)
            else:
                self._add_result_to_targets(rule.targets, result)
        if self._initialize_rules_to_run:
            self._initialize_rules_to_run.remove(rule)

    def check_invariants(self):
        for invar in self.invariants():
            if invar.precondition and not invar.precondition(self):
                continue
            invar.function(self)
