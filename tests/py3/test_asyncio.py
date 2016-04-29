# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from __future__ import division, print_function, absolute_import

import asyncio
import unittest
from unittest import TestCase

import hypothesis.strategies as st
from hypothesis import given, assume


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
