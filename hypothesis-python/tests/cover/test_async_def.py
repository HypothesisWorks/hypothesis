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
from unittest import TestCase

from hypothesis import assume, given, strategies as st


class TestAsyncioRun(TestCase):
    timeout = 5

    def execute_example(self, f):
        asyncio.run(f())

    @given(st.text())
    async def test_foo(self, x):
        assume(x)
        await asyncio.sleep(0.001)
        assert x
