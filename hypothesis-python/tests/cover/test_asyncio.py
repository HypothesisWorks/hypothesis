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
import warnings
from unittest import TestCase

import pytest

from hypothesis import assume, given, strategies as st
from hypothesis.internal.compat import PYPY

from tests.common.utils import skipif_emscripten


def coro_decorator(f):
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=DeprecationWarning)
        try:
            return asyncio.coroutine(f)
        except AttributeError:
            pytest.skip("needs fixing for asyncio version", allow_module_level=True)


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
                x = f()
                if x is not None:
                    yield from x
            except BaseException as e:
                error = e

        coro = coro_decorator(g)
        future = asyncio.wait_for(coro(), timeout=self.timeout)
        self.loop.run_until_complete(future)
        if error is not None:
            raise error

    @pytest.mark.skipif(PYPY, reason="Error in asyncio.new_event_loop()")
    @given(x=st.text())
    @coro_decorator
    def test_foo(self, x):
        assume(x)
        yield from asyncio.sleep(0.001)
        assert x


class TestAsyncioRun(TestCase):
    # In principle, these tests could indeed run on emscripten if we grab the existing
    # event loop and run them there.  However, that seems to have hit an infinite loop
    # and so we're just skipping them for now and will revisit later.

    def execute_example(self, f):
        asyncio.run(f())

    @skipif_emscripten
    @given(x=st.text())
    @coro_decorator
    def test_foo_yield_from(self, x):
        assume(x)
        yield from asyncio.sleep(0.001)
        assert x

    @skipif_emscripten
    @given(st.text())
    async def test_foo_await(self, x):
        assume(x)
        await asyncio.sleep(0.001)
        assert x
