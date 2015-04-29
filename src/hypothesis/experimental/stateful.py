# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

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

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from random import Random
from unittest import TestCase

from hypothesis.core import find
from hypothesis.types import Stream
from hypothesis.errors import Flaky, NoSuchExample
from hypothesis.settings import Settings
from hypothesis.reporting import report
from hypothesis.utils.show import show
from hypothesis.internal.compat import hrange
from hypothesis.internal.distributions import geometric
from hypothesis.searchstrategy.strategies import BadData, BuildContext, \
    SearchStrategy


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
        raise NotImplementedError('%r.steps()' % (self,))

    def execute_step(self, step):
        """Execute a step that has been previously drawn from self.steps()"""
        raise NotImplementedError('%r.execute_steps()' % (self,))

    def print_step(self, step):
        """Print a step to the current reporter.

        This is called right before a step is executed.

        """
        self.step_count = getattr(self, 'step_count', 0) + 1
        report('Step #%d: %s' % (self.step_count, show(step)))

    def teardown(self):
        """Called after a run has finished executing to clean up any necessary
        state.

        Does nothing by default

        """
        pass

    @classmethod
    def find_breaking_runner(state_machine_class):
        def is_breaking_run(runner):
            try:
                runner.run(state_machine_class())
                return False
            except Exception:
                return True
        return find(
            StateMachineSearchStrategy(), is_breaking_run, Settings.default,
        )

    _test_case_cache = {}

    @classmethod
    def to_test_case(state_machine_class):
        try:
            return state_machine_class._test_case_cache[state_machine_class]
        except KeyError:
            pass

        class StateMachineTestCase(TestCase):

            def runTest(self):
                try:
                    breaker = state_machine_class.find_breaking_runner()
                except NoSuchExample:
                    return

                breaker.run(state_machine_class(), print_steps=True)
                raise Flaky(
                    'Run failed initially by succeeded on a second try'
                )

        base_name = state_machine_class.__name__
        StateMachineTestCase.__name__ = (
            base_name + '.TestCase'
        )
        StateMachineTestCase.__qualname__ = (
            getattr(state_machine_class, '__qualname__', base_name) +
            '.TestCase'
        )
        state_machine_class._test_case_cache[state_machine_class] = (
            StateMachineTestCase
        )
        return StateMachineTestCase


def seeds(starting):
    random = Random(starting)

    def gen():
        while True:
            yield random.getrandbits(64)
    return Stream(gen())


# Sentinel value used to mark entries as deleted.
TOMBSTONE = [object(), 'TOMBSTONE FOR STATEFUL TESTING']


class StateMachineRunner(object):

    """A StateMachineRunner is a description of how to run a state machine.

    It contains values that it will use to shape the examples.

    """

    def __init__(self, parameter_seed, template_seed, n_steps, record=None):
        self.parameter_seed = parameter_seed
        self.template_seed = template_seed
        self.n_steps = n_steps

        self.templates = seeds(template_seed)
        self.record = list(record or ())

        self.shows = []

    def __trackas__(self):
        return (
            StateMachineRunner,
            self.parameter_seed, self.template_seed,
            self.n_steps,
            [data[1] for data in self.record],
        )

    def __repr__(self):
        trail = []
        for s in self.shows:
            if s is not None:
                trail.append(s)
        return (
            'StateMachineRunner(%s)' % (
                ', '.join(trail)
            )
        )

    def run(self, state_machine, print_steps=False):
        try:
            for i in hrange(self.n_steps):
                strategy = state_machine.steps()

                template_set = False
                if i < len(self.record):
                    if self.record[i] is TOMBSTONE:
                        if i < len(self.shows):
                            self.shows[i] = None
                        continue
                    _, data = self.record[i]
                    try:
                        template = strategy.from_basic(data)
                        template_set = True
                    except BadData:
                        pass
                if not template_set:
                    parameter = strategy.draw_parameter(Random(
                        self.parameter_seed
                    ))
                    template = strategy.draw_template(
                        BuildContext(Random(self.templates[i])), parameter)

                new_record = (
                    strategy, strategy.to_basic(template)
                )
                if i < len(self.record):
                    self.record[i] = new_record
                else:
                    self.record.append(new_record)

                value = strategy.reify(template)

                if i < len(self.shows):
                    self.shows[i] = show(value)
                else:
                    self.shows.append(show(value))
                if print_steps:
                    state_machine.print_step(value)
                state_machine.execute_step(value)
        finally:
            state_machine.teardown()


class StateMachineSearchStrategy(SearchStrategy):

    def reify(self, template):
        return template

    def produce_parameter(self, random):
        return (
            random.random(),
            random.getrandbits(64),
        )

    def produce_template(self, context, parameter_value):
        size_dropoff, parameter_seed = parameter_value
        size = min(1000, 1 + geometric(context.random, size_dropoff))
        return StateMachineRunner(
            parameter_seed,
            context.random.getrandbits(64),
            n_steps=size,
        )

    def simplifiers(self, random, template):
        yield self.cut_steps
        yield self.random_discards
        yield self.delete_elements
        for i in hrange(len(template.record)):
            if template.record[i] != TOMBSTONE:
                strategy, data = template.record[i]
                child_template = strategy.from_basic(data)
                for simplifier in strategy.simplifiers(random, child_template):
                    yield self.convert_simplifier(strategy, simplifier, i)

    def convert_simplifier(self, strategy, simplifier, i):
        def accept(random, template):
            if i >= len(template.record):
                return
            if template.record[i] == TOMBSTONE:
                return
            try:
                reconstituted = strategy.from_basic(template.record[i][1])
            except BadData:
                return

            for t in simplifier(random, reconstituted):
                new_record = list(template.record)
                new_record[i] = (strategy, strategy.to_basic(t))
                yield StateMachineRunner(
                    parameter_seed=template.parameter_seed,
                    template_seed=template.template_seed,
                    n_steps=template.n_steps,
                    record=new_record,
                )
        accept.__name__ = 'convert_simplifier(%s, %d)' % (
            simplifier.__name__, i
        )
        return accept

    def random_discards(self, random, template):
        for _ in hrange(10):
            new_record = list(template.record)
            for i in hrange(len(template.record)):
                if new_record[i] != TOMBSTONE and random.randint(0, 1):
                    new_record[i] = TOMBSTONE
            yield StateMachineRunner(
                parameter_seed=template.parameter_seed,
                template_seed=template.template_seed,
                n_steps=template.n_steps,
                record=new_record,
            )

    def cut_steps(self, random, template):
        mid = 0
        while True:
            next_mid = (template.n_steps + mid) // 2
            if next_mid == mid:
                break
            mid = next_mid
            yield StateMachineRunner(
                parameter_seed=template.parameter_seed,
                template_seed=template.template_seed,
                n_steps=mid,
                record=template.record,
            )
            new_record = list(template.record)
            for i in hrange(mid):
                new_record[i] = TOMBSTONE
            yield StateMachineRunner(
                parameter_seed=template.parameter_seed,
                template_seed=template.template_seed,
                n_steps=template.n_steps,
                record=new_record,
            )

    def delete_elements(self, random, template):
        for i in hrange(len(template.record)):
            if template.record[i] != TOMBSTONE:
                new_record = list(template.record)
                new_record[i] = TOMBSTONE
                yield StateMachineRunner(
                    parameter_seed=template.parameter_seed,
                    template_seed=template.template_seed,
                    n_steps=template.n_steps,
                    record=new_record,
                )
