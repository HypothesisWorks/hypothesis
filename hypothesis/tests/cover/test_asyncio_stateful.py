# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import asyncio
import contextvars

import pytest

from hypothesis import settings, strategies as st
from hypothesis.errors import InvalidDefinition
from hypothesis.stateful import (
    AsyncioRuleBasedStateMachine,
    Bundle,
    RuleBasedStateMachine,
    consumes,
    initialize,
    invariant,
    rule,
    run_state_machine_as_test,
)

from tests.common.utils import skipif_emscripten

VAR = contextvars.ContextVar("VAR")


@skipif_emscripten
def test_runs_async_and_sync_methods_on_one_loop_per_test_case():
    loops_per_case = []

    class Machine(AsyncioRuleBasedStateMachine):
        things = Bundle("things")

        @initialize()
        async def start(self):
            self.loop = asyncio.get_running_loop()
            self.queue = asyncio.Queue()
            self.calls = set()
            VAR.set("set in initialize")

        @rule(target=things, x=st.integers())
        async def make(self, x):
            assert asyncio.get_running_loop() is self.loop
            await self.queue.put(x)
            self.calls.add("make")
            return x

        @rule(thing=consumes(things))
        async def use(self, thing):
            assert isinstance(thing, int)
            assert VAR.get() == "set in initialize"
            assert isinstance(await self.queue.get(), int)
            self.calls.add("use")

        @rule()
        def sync_rule(self):
            self.calls.add("sync")

        @invariant()
        async def loop_is_running(self):
            assert asyncio.get_running_loop() is self.loop

        async def teardown(self):
            assert asyncio.get_running_loop() is self.loop
            loops_per_case.append((self.loop, self.calls))

    run_state_machine_as_test(Machine, settings=settings(max_examples=20))

    loops = [loop for loop, _ in loops_per_case]
    assert len(set(map(id, loops))) == len(loops)
    assert all(loop.is_closed() for loop in loops)
    assert set().union(*(calls for _, calls in loops_per_case)) == {
        "make",
        "use",
        "sync",
    }


@skipif_emscripten
def test_closes_the_loop_and_cancels_leftover_tasks_when_a_rule_fails():
    tasks = []

    @settings(max_examples=10, print_blob=False)
    class Machine(AsyncioRuleBasedStateMachine):
        @rule()
        async def start_background_task_then_fail(self):
            tasks.append(asyncio.create_task(asyncio.sleep(3600)))
            raise ValueError("found it")

    with pytest.raises(ValueError, match="found it"):
        run_state_machine_as_test(Machine)
    assert tasks
    assert all(task.cancelled() for task in tasks)


@skipif_emscripten
def test_reports_the_failing_async_steps():
    @settings(max_examples=50, print_blob=False)
    class Machine(AsyncioRuleBasedStateMachine):
        @rule(x=st.integers())
        async def fail_on_big(self, x):
            await asyncio.sleep(0)
            assert x < 10

    with pytest.raises(AssertionError) as err:
        run_state_machine_as_test(Machine)
    assert "\n".join(err.value.__notes__).strip().splitlines()[-3:] == [
        "state = Machine()",
        "state.fail_on_big(x=10)",
        "state.teardown()",
    ]


class AsyncRule(RuleBasedStateMachine):
    @rule()
    async def r(self):
        pass


class AsyncInitialize(RuleBasedStateMachine):
    @initialize()
    async def i(self):
        pass

    @rule()
    def r(self):
        pass


class AsyncInvariant(RuleBasedStateMachine):
    @rule()
    def r(self):
        pass

    @invariant()
    async def inv(self):
        pass


class AsyncTeardown(RuleBasedStateMachine):
    @rule()
    def r(self):
        pass

    async def teardown(self):
        pass


@pytest.mark.parametrize(
    "machine", [AsyncRule, AsyncInitialize, AsyncInvariant, AsyncTeardown]
)
def test_sync_machine_rejects_async_methods(machine):
    with pytest.raises(InvalidDefinition, match="AsyncioRuleBasedStateMachine"):
        run_state_machine_as_test(machine)
