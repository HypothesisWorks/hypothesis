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
import sys
from typing import Callable

import pytest

from hypothesis import errors, given, reject, strategies as st
from hypothesis.internal.compat import ExceptionGroup
from hypothesis.strategies import DataObject

# this file is not typechecked by mypy, which only runs py310

if sys.version_info < (3, 11):
    pytest.skip("asyncio.TaskGroup not available on <py3.11", allow_module_level=True)


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
            data.draw(st.booleans().filter(pred))

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
    @given(st.data())
    def test_function(data):
        async def task(d: DataObject) -> None:
            d.conjecture_data.mark_invalid()

        async def _main(d: DataObject) -> None:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(task(d))
                tg.create_task(task(d))

        asyncio.run(_main(data))

    # multiple stoptests -> single stoptest -> unsatisfiable
    with pytest.raises(errors.Unsatisfiable):
        test_function()


def test_exceptiongroup_stop_and_hypothesisexception() -> None:
    # group with stoptest+invalidargument -> invalidargument
    @given(st.data())
    def test_function(data):
        async def task_stoptest(d: DataObject) -> None:
            # only mark some runs as invalid to not raise Unsatisfiable
            if d.draw(st.integers(min_value=0, max_value=1)) == 1:
                d.conjecture_data.mark_invalid()

        async def task_invalid_argument(d: DataObject) -> None:
            d.draw(st.integers(max_value=2, min_value=3))

        async def _main(d: DataObject) -> None:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(task_stoptest(d))
                tg.create_task(task_invalid_argument(d))

        asyncio.run(_main(data))

    with pytest.raises(errors.InvalidArgument):
        test_function()


def test_exceptiongroup_multiple_hypothesisexception() -> None:
    # multiple UnsatisfiedAssumption => first one is reraised => engine suppresses it

    @given(st.integers(min_value=0, max_value=3))
    def test_function(val: int) -> None:
        async def task(value: int) -> None:
            if value == 0:
                reject()

        async def _main(value: int) -> None:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(task(value))
                tg.create_task(task(value))

        asyncio.run(_main(val))

    test_function()


def test_exceptiongroup_multiple_InvalidArgument() -> None:
    # multiple InvalidArgument => only first one is reraised... which seems bad.
    # But raising a group might break ghostwriter(?)

    @given(st.data())
    def test_function(data: DataObject) -> None:
        async def task1(d: DataObject) -> None:
            d.draw(st.integers(max_value=1, min_value=3))

        async def task2(d: DataObject) -> None:
            d.draw(st.integers(max_value=2, min_value=3))

        async def _main(d: DataObject) -> None:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(task1(d))
                tg.create_task(task2(d))

        asyncio.run(_main(data))

    with pytest.raises(errors.InvalidArgument):
        test_function()
