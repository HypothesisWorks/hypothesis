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
from typing import Callable

import pytest

from hypothesis import errors, given, strategies as st
from hypothesis.internal.compat import ExceptionGroup
from hypothesis.strategies import DataObject


def test_exceptiongroup_discard_frozen():
    """Basic test that raises Frozen+Unsatisfiable.
    Frozen is thrown out, and Unsatisfiable is raised"""

    @given(st.data())
    def test_function(data):
        async def task(pred):
            return data.draw(st.booleans().filter(pred))

        async def _main():
            async with asyncio.TaskGroup() as tg:
                tg.create_task(task(bool))
                tg.create_task(task(lambda _: False))

        asyncio.run(_main())

    with pytest.raises(errors.Unsatisfiable):
        test_function()


def test_exceptiongroup_nested() -> None:
    @given(st.data())
    def test_function(data: DataObject) -> None:
        async def task(pred: Callable[[bool], bool]) -> None:
            return data.draw(st.booleans().filter(pred))

        async def _main() -> None:
            async with asyncio.TaskGroup():
                async with asyncio.TaskGroup() as tg2:
                    tg2.create_task(task(bool))
                    tg2.create_task(task(lambda _: False))

        asyncio.run(_main())

    with pytest.raises(errors.Unsatisfiable):
        test_function()


def test_exceptiongroup_user_originated() -> None:
    @given(st.data())
    def test_function(data):
        raise ExceptionGroup("foo", [ValueError(), ValueError()])

    with pytest.raises(ExceptionGroup) as exc_info:
        test_function()
    e = exc_info.value
    assert e.message == "foo"
    assert isinstance(e, ExceptionGroup)
    assert len(e.exceptions) == 2
    assert all(isinstance(child_e, ValueError) for child_e in e.exceptions)

    @given(st.data())
    def test_single_exc_group(data):
        raise ExceptionGroup("important message for user", [ValueError()])

    with pytest.raises(ExceptionGroup) as exc_info:
        test_single_exc_group()
    e = exc_info.value
    assert e.message == "important message for user"
    assert isinstance(e, ExceptionGroup)
    assert len(e.exceptions) == 1
    assert isinstance(e.exceptions[0], ValueError)


def test_exceptiongroup_multiple_stop() -> None:
    # or well, I'm trying to get multiple StopTest, but instead I'm getting a strange
    # AttributeError
    @given(st.data())
    def test_function(data):
        async def task(d: DataObject) -> None:
            d.conjecture_data.mark_interesting()

        async def _main(d: DataObject) -> None:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(task(d))
                tg.create_task(task(d))

        asyncio.run(_main(data))

    test_function()


# if intended, will probably remove this test, and either way probably belong somewhere else
def test_frozen_things():
    # Hypothesis reraises the TypeError as a StopTest, because the data is Frozen.
    # Doesn't seem great, but I suppose it is intentional?
    @given(st.data())
    def foo(data):
        data.conjecture_data.freeze()
        raise TypeError("oops")

    foo()


# if above is intended, then this is supposedly also intended?
def test_frozen_data_and_critical_user_exception():
    @given(st.data())
    def test_function(data):
        data.conjecture_data.freeze()

        async def task(d: DataObject) -> None:
            d.draw(st.booleans())

        async def task2() -> None:
            raise TypeError("Critical error")

        async def _main(d: DataObject) -> None:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(task(d))
                tg.create_task(task2())

        asyncio.run(_main(data))

    # does not raise anything, the TypeError is suppressed
    test_function()
    # with pytest.raises(ExceptionGroup) as exc_info:
    # e = exc_info.value
    # assert isinstance(e, ExceptionGroup)
    # assert len(e.exceptions) == 2
    # assert isinstance(e.exceptions[0], errors.Frozen)
    # assert isinstance(e.exceptions[1], TypeError)
