import unittest
from unittest import TestCase

import asyncio
from hypothesis import given, assume
import hypothesis.strategies as st


class TestAsyncio(TestCase):

    timeout = 5

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def execute_example(self, f):
        error = None

        def g():
            nonlocal error
            try:
                yield from f()
            except BaseException as e:
                error = e
        coro = asyncio.coroutine(f)
        future = asyncio.wait_for(coro(),
                                  timeout=self.timeout)
        self.loop.run_until_complete(future)
        if error is not None:
            raise error

    @given(st.text())
    def test_foo(self, x):
        assume(x)
        yield from asyncio.sleep(0.001)
        assert x

if __name__ == '__main__':
    unittest.main()
