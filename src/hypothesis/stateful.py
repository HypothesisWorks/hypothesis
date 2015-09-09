# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

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
from random import Random
from unittest import TestCase
from collections import namedtuple

from hypothesis.core import find
from hypothesis.errors import Flaky, NoSuchExample, InvalidDefinition, \
    UnsatisfiedAssumption
from hypothesis.settings import Settings, Verbosity
from hypothesis.reporting import report, verbose_report, current_verbosity
from hypothesis.internal.compat import hrange, integer_types
from hypothesis.searchstrategy.misc import JustStrategy, \
    SampledFromStrategy
from hypothesis.searchstrategy.strategies import BadData, strategy, \
    check_length, SearchStrategy, check_data_type, one_of_strategies
from hypothesis.searchstrategy.collections import TupleStrategy, \
    FixedKeysDictStrategy

Settings.define_setting(
    name=u'stateful_step_count',
    default=50,
    description="""
Number of steps to run a stateful program for before giving up on it breaking.
"""
)


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
        except (InvalidDefinition, UnsatisfiedAssumption):
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
    if settings.database is not None:
        storage = settings.database.storage(
            getattr(
                state_machine_factory, u'__name__',
                type(state_machine_factory).__name__))
    else:
        storage = None

    return find(
        search_strategy,
        is_breaking_run,
        settings=settings,
        storage=storage,
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

    breaker.run(state_machine_factory(), print_steps=True)
    raise Flaky(
        u'Run failed initially by succeeded on a second try'
    )


class GenericStateMachine(object):

    """A GenericStateMachine is the basic entry point into Hypothesis's
    approach to stateful testing.

    The intent is for it to be subclassed to provide state machine descriptions

    The way this is used is that Hypothesis will repeatedly execute something
    that looks something like:

    x = MyStatemachineSubclass()
    for _ in range(n_steps):
        x.execute_step(x.steps().example())

    And if this ever produces an error it will shrink it down to a small
    sequence of example choices demonstrating that.

    """

    def steps(self):
        """Return a SearchStrategy instance the defines the available next
        steps."""
        raise NotImplementedError(u'%r.steps()' % (self,))

    def execute_step(self, step):
        """Execute a step that has been previously drawn from self.steps()"""
        raise NotImplementedError(u'%r.execute_steps()' % (self,))

    def print_step(self, step):
        """Print a step to the current reporter.

        This is called right before a step is executed.

        """
        self.step_count = getattr(self, u'step_count', 0) + 1
        report(u'Step #%d: %s' % (self.step_count, repr(step)))

    def teardown(self):
        """Called after a run has finished executing to clean up any necessary
        state.

        Does nothing by default

        """
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
            settings = Settings()

            def runTest(self):
                run_state_machine_as_test(state_machine_class)

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


def seeds(starting, n_steps):
    random = Random(starting)

    result = []
    for _ in hrange(n_steps):
        result.append(random.getrandbits(64))
    return result


# Sentinel value used to mark entries as deleted.
TOMBSTONE = [object(), [u'TOMBSTONE FOR STATEFUL TESTING']]


class StateMachineRunner(object):

    """A StateMachineRunner is a description of how to run a state machine.

    It contains values that it will use to shape the examples.

    """

    def __init__(
        self, parameter_seed, template_seed, n_steps,
        record=None, templates=None,
    ):
        self.parameter_seed = parameter_seed
        self.template_seed = template_seed
        self.n_steps = n_steps
        assert 0 <= n_steps <= 1000000

        self.templates = templates or seeds(template_seed, n_steps)
        assert len(self.templates) >= n_steps
        self.record = list(record or ())

    def __eq__(self, other):
        return isinstance(other, StateMachineRunner) and (
            self.parameter_seed == other.parameter_seed and
            self.template_seed == other.template_seed and
            self.n_steps == other.n_steps
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((
            self.parameter_seed,
            self.template_seed,
            self.n_steps,
        ))

    def __trackas__(self):
        return (
            StateMachineRunner,
            self.parameter_seed, self.template_seed,
            self.n_steps,
            [data[1] for data in self.record],
        )

    def __repr__(self):
        return (
            u'StateMachineRunner(%d/%d steps)' % (
                len([t for t in self.record if t != TOMBSTONE]),
                self.n_steps,
            )
        )

    def run(self, state_machine, print_steps=None):
        if print_steps is None:
            print_steps = current_verbosity() >= Verbosity.debug

        try:
            for i in hrange(self.n_steps):
                strategy = state_machine.steps()

                template_set = False
                if i < len(self.record):
                    if self.record[i] is TOMBSTONE:
                        continue
                    _, data = self.record[i]
                    data = list(data)
                    for data_index in hrange(len(data) - 1, -1, -1):
                        try:
                            template = strategy.from_basic(data[data_index])
                            template_set = True
                            break
                        except BadData:
                            pass
                    if template_set:
                        data[data_index], data[-1] = (
                            data[-1], data[data_index]
                        )
                else:
                    data = []
                if not template_set:
                    parameter = strategy.draw_parameter(Random(
                        self.parameter_seed
                    ))
                    template = strategy.draw_template(
                        Random(self.templates[i]), parameter)
                    data.append(strategy.to_basic(template))

                new_record = (
                    strategy, data,
                )
                if i < len(self.record):
                    self.record[i] = new_record
                else:
                    self.record.append(new_record)

                strategy.from_basic(self.record[i][1][-1])
                value = strategy.reify(template)

                if print_steps:
                    state_machine.print_step(value)
                state_machine.execute_step(value)
        finally:
            state_machine.teardown()


class StateMachineSearchStrategy(SearchStrategy):

    def __init__(self, settings=None):
        self.program_size = (settings or Settings.default).stateful_step_count

    def __repr__(self):
        return u'StateMachineSearchStrategy()'

    def reify(self, template):
        return template

    def draw_parameter(self, random):
        return (
            random.getrandbits(64)
        )

    def draw_template(self, random, parameter_value):
        parameter_seed = parameter_value
        return StateMachineRunner(
            parameter_seed,
            random.getrandbits(64),
            n_steps=self.program_size,
        )

    def to_basic(self, template):
        return [
            template.parameter_seed,
            template.template_seed,
            template.n_steps,
            [
                [data[1]]
                if data != TOMBSTONE else None
                for data in template.record
            ]
        ]

    def from_basic(self, data):
        check_data_type(list, data)
        check_length(4, data)
        check_data_type(integer_types, data[0])
        check_data_type(integer_types, data[1])
        check_data_type(integer_types, data[2])
        check_data_type(list, data[3])

        if data[2] < 0:
            raise BadData(u'Invalid negative number of steps: %d' % (
                data[2],
            ))
        if data[2] > Settings.default.stateful_step_count * 1000:
            raise BadData(u'Implausibly large number of steps: %d' % (
                data[2],
            ))

        record = []

        for record_data in data[3]:
            if record_data is None:
                record.append(TOMBSTONE)
            else:
                check_data_type(list, record_data)
                check_length(1, record_data)
                record.append((None, record_data[0]))
        return StateMachineRunner(
            parameter_seed=data[0], template_seed=data[1],
            n_steps=data[2],
            record=record,
        )

    def simplifiers(self, random, template):
        yield self.cut_steps
        yield self.random_discards
        yield self.delete_elements
        for i in hrange(len(template.record)):
            if template.record[i] != TOMBSTONE:
                strategy, data = template.record[i]
                if strategy is None:
                    continue
                child_template = strategy.from_basic(data[-1])
                for simplifier in strategy.simplifiers(random, child_template):
                    yield self.convert_simplifier(strategy, simplifier, i)

    def convert_simplifier(self, strategy, simplifier, i):
        def accept(random, template):
            if i >= len(template.record):
                return
            if template.record[i][0] is not strategy:
                return

            reconstituted = strategy.from_basic(template.record[i][1][-1])

            for t in simplifier(random, reconstituted):
                new_record = list(template.record)
                existing = new_record[i]
                new_record[i] = (existing[0], list(existing[1]))
                new_record[i][1][-1] = strategy.to_basic(t)
                yield StateMachineRunner(
                    parameter_seed=template.parameter_seed,
                    template_seed=template.template_seed,
                    templates=template.templates,
                    n_steps=template.n_steps,
                    record=new_record,
                )
        accept.__name__ = str(u'convert_simplifier(%s, %d)' % (
            simplifier.__name__, i
        ))
        return accept

    def random_discards(self, random, template):
        live = len([
            r for r in template.record if r != TOMBSTONE
        ])
        if live < 10:
            return

        for k in hrange(1, 8):
            for _ in hrange(10):
                new_record = list(template.record)
                for i in hrange(len(template.record)):
                    if new_record[i] != TOMBSTONE:
                        if random.randint(0, 9) <= k:
                            new_record[i] = TOMBSTONE
                yield StateMachineRunner(
                    parameter_seed=template.parameter_seed,
                    template_seed=template.template_seed,
                    templates=template.templates,
                    n_steps=template.n_steps,
                    record=new_record,
                )

    def cut_steps(self, random, template):
        if len(template.record) < template.n_steps:
            yield StateMachineRunner(
                parameter_seed=template.parameter_seed,
                template_seed=template.template_seed,
                templates=template.templates,
                n_steps=len(template.record),
                record=template.record,
            )
        mid = 0
        while True:
            next_mid = (template.n_steps + mid) // 2
            if next_mid == mid:
                break
            mid = next_mid
            yield StateMachineRunner(
                parameter_seed=template.parameter_seed,
                template_seed=template.template_seed,
                templates=template.templates,
                n_steps=mid,
                record=template.record,
            )
            new_record = list(template.record)
            for i in hrange(min(mid, len(new_record))):
                new_record[i] = TOMBSTONE
            yield StateMachineRunner(
                parameter_seed=template.parameter_seed,
                template_seed=template.template_seed,
                templates=template.templates,
                n_steps=template.n_steps,
                record=new_record,
            )

    def delete_elements(self, random, template):
        deletes = 0
        indices = list(hrange(len(template.record)))
        random.shuffle(indices)
        for i in indices:
            if deletes >= 10:
                break
            if template.record[i] != TOMBSTONE:
                deletes += 1
                new_record = list(template.record)
                new_record[i] = TOMBSTONE
                yield StateMachineRunner(
                    parameter_seed=template.parameter_seed,
                    template_seed=template.template_seed,
                    templates=template.templates,
                    n_steps=template.n_steps,
                    record=new_record,
                )


Rule = namedtuple(
    u'Rule',
    (u'targets', u'function', u'arguments')

)

Bundle = namedtuple(u'Bundle', (u'name',))


RULE_MARKER = u'hypothesis_stateful_rule'


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
        if not hasattr(f, RULE_MARKER):
            setattr(f, RULE_MARKER, [])
        getattr(f, RULE_MARKER).append(
            Rule(
                targets=tuple(converted_targets), arguments=kwargs, function=f
            )
        )
        return f
    return accept


VarReference = namedtuple(u'VarReference', (u'name',))


class SimpleSampledFromStrategy(SampledFromStrategy):

    def draw_parameter(self, random):
        return None

    def draw_template(self, random, parameter_value):
        return random.randint(0, len(self.elements) - 1)


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
    _base_rules_per_class = {}

    def __init__(self):
        if not self.rules():
            raise InvalidDefinition(u'Type %s defines no rules' % (
                type(self).__name__,
            ))
        self.bundles = {}
        self.name_counter = 1
        self.names_to_values = {}

    def __repr__(self):
        return u'%s(%s)' % (
            type(self).__name__,
            repr(self.bundles),
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
            for r in getattr(v, RULE_MARKER, ()):
                cls.define_rule(
                    r.targets, r.function, r.arguments
                )
        cls._rules_per_class[cls] = cls._base_rules_per_class.pop(cls, [])
        return cls._rules_per_class[cls]

    @classmethod
    def define_rule(cls, targets, function, arguments):
        converted_arguments = {}
        for k, v in arguments.items():
            if not isinstance(v, Bundle):
                v = strategy(v)
            converted_arguments[k] = v
        if cls in cls._rules_per_class:
            target = cls._rules_per_class[cls]
        else:
            target = cls._base_rules_per_class.setdefault(cls, [])

        return target.append(
            Rule(targets, function, converted_arguments)
        )

    def steps(self):
        strategies = []
        for rule in self.rules():
            converted_arguments = {}
            valid = True
            for k, v in rule.arguments.items():
                if isinstance(v, Bundle):
                    bundle = self.bundle(v.name)
                    if not bundle:
                        valid = False
                        break
                    else:
                        v = SimpleSampledFromStrategy(bundle)
                converted_arguments[k] = v
            if valid:
                strategies.append(TupleStrategy((
                    JustStrategy(rule),
                    FixedKeysDictStrategy(converted_arguments)
                ), tuple))
        if not strategies:
            raise InvalidDefinition(
                u'No progress can be made from state %r' % (self,)
            )
        return one_of_strategies(strategies)

    def print_step(self, step):
        rule, data = step
        data_repr = {}
        for k, v in data.items():
            if isinstance(v, VarReference):
                data_repr[k] = v.name
            else:
                data_repr[k] = repr(v)
        self.step_count = getattr(self, u'step_count', 0) + 1
        report(u'Step #%d: %s%s(%s)' % (
            self.step_count,
            u'%s = ' % (self.upcoming_name(),) if rule.targets else u'',
            rule.function.__name__,
            u', '.join(u'%s=%s' % kv for kv in data_repr.items())
        ))

    def execute_step(self, step):
        rule, data = step
        data = dict(data)
        for k, v in data.items():
            if isinstance(v, VarReference):
                data[k] = self.names_to_values[v.name]
        result = rule.function(self, **data)
        if rule.targets:
            name = self.new_name()
            self.names_to_values[name] = result
            for target in rule.targets:
                self.bundle(target).append(VarReference(name))
