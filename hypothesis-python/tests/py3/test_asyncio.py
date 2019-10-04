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

from __future__ import absolute_import, division, print_function

import asyncio
import sys
import unittest
from unittest import TestCase

import pytest

import hypothesis.strategies as st
from hypothesis import assume, given
from hypothesis.internal.compat import PYPY


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

        coro = asyncio.coroutine(g)
        future = asyncio.wait_for(coro(), timeout=self.timeout)
        self.loop.run_until_complete(future)
        if error is not None:
            raise error

    @pytest.mark.skipif(PYPY, reason="Error in asyncio.new_event_loop()")
    @pytest.mark.skipif(sys.version_info[:2] >= (3, 8), reason="deprecated @coroutine")
    @given(st.text())
    @asyncio.coroutine
    def test_foo(self, x):
        assume(x)
        yield from asyncio.sleep(0.001)
        assert x


class TestAsyncioRun(TestCase):

    timeout = 5

    def execute_example(self, f):
        asyncio.run(f())

    @pytest.mark.skipif(sys.version_info[:2] < (3, 7), reason="asyncio.run() is new")
    @given(st.text())
    @asyncio.coroutine
    def test_foo(self, x):
        assume(x)
        yield from asyncio.sleep(0.001)
        assert x


if __name__ == "__main__":
    unittest.main()
