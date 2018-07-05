# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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
from copy import copy
from unittest import TestCase

import attr

import hypothesis.internal.conjecture.utils as cu
from hypothesis.core import find
from hypothesis.errors import Flaky, NoSuchExample, InvalidDefinition, \
    HypothesisException
from hypothesis.control import BuildContext
from hypothesis._settings import Verbosity
from hypothesis._settings import settings as Settings
from hypothesis.reporting import report, verbose_report, current_verbosity
from hypothesis.strategies import just, one_of, runner, tuples, \
    fixed_dictionaries
from hypothesis.vendor.pretty import CUnicodeIO, RepresentationPrinter
from hypothesis.internal.reflection import proxies, nicerepr
from hypothesis.internal.conjecture.data import StopTest
from hypothesis.internal.conjecture.utils import integer_range, \
    calc_label_from_name
from hypothesis.searchstrategy.strategies import SearchStrategy
from hypothesis.stateful import GenericStateMachine, StateMachineRunner, StateMachineSearchStrategy, TestCaseProperty, RuleBasedStateMachine, VarReference
import trio
from trio.testing import trio_test


class TrioGenericAsyncStateMachine(GenericStateMachine):
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

    def get_root_nursery(self):
        return getattr(self, '_nursery', None)

    def _custom_runner(self, data, print_steps, should_continue):

        async def _run():
            async with trio.open_nursery() as self._nursery:
                try:
                    if print_steps:
                        self.print_start()
                    await self.check_invariants()

                    while should_continue.more():
                        value = data.draw(self.steps())
                        if print_steps:
                            self.print_step(value)
                        await self.execute_step(value)
                        await self.check_invariants()
                finally:
                    if print_steps:
                        self.print_end()
                    await self.teardown()
                    self._nursery.cancel_scope.cancel()

        trio_test(_run)()

    async def execute_step(self, step):
        """Execute a step that has been previously drawn from self.steps()"""
        raise NotImplementedError(u'%r.execute_step()' % (self,))

    async def teardown(self):
        """Called after a run has finished executing to clean up any necessary
        state.

        Does nothing by default.
        """
        pass

    async def check_invariants(self):
        """Called after initializing and after executing each step."""
        pass


class TrioRuleBasedAsyncStateMachine(TrioGenericAsyncStateMachine, RuleBasedStateMachine):
    """A RuleBasedStateMachine gives you a more structured way to define state
    machines.

    The idea is that a state machine carries a bunch of types of data
    divided into Bundles, and has a set of rules which may read data
    from bundles (or just from normal strategies) and push data onto
    bundles. At any given point a random applicable rule will be
    executed.
    """

    async def execute_step(self, step):
        rule, data = step
        data = dict(data)
        for k, v in list(data.items()):
            if isinstance(v, VarReference):
                data[k] = self.names_to_values[v.name]
        result = await rule.function(self, **data)
        if rule.targets:
            name = self.new_name()
            self.names_to_values[name] = result
            self.__printer.singleton_pprinters.setdefault(
                id(result), lambda obj, p, cycle: p.text(name)
            )
            for target in rule.targets:
                self.bundle(target).append(VarReference(name))
        if self._initialize_rules_to_run:
            self._initialize_rules_to_run.remove(rule)

    async def check_invariants(self):
        for invar in self.invariants():
            if invar.precondition and not invar.precondition(self):
                continue
            await invar.function(self)
