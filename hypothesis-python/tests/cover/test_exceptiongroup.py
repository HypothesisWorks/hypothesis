import sys
import asyncio

from trio.testing import RaisesGroup
from hypothesis import errors, given, strategies as st
import pytest

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup

def test_exceptiongroup():
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

def test_exceptiongroup_nested():
    @given(st.data())
    def test_function(data):
        async def task(pred):
            return data.draw(st.booleans().filter(pred))

        async def _main():
            async with asyncio.TaskGroup():
                async with asyncio.TaskGroup() as tg2:
                    tg2.create_task(task(bool))
                    tg2.create_task(task(lambda _: False))
        asyncio.run(_main())
    with pytest.raises(errors.Unsatisfiable):
        test_function()


def test_exceptiongroup_user_originated():
    @given(st.data())
    def test_function(data):
        raise ExceptionGroup("foo", [ValueError(), ValueError()])
    with RaisesGroup(ValueError, ValueError, match="foo"):
        test_function()


    @given(st.data())
    def test_single_exc_group(data):
        raise ExceptionGroup("important message for user", [ValueError()])

    with RaisesGroup(ValueError, match="important message for user"):
        test_single_exc_group()
