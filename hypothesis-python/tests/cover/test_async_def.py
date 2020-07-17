# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import asyncio
import sys
from unittest import TestCase

import pytest

from hypothesis import assume, given, strategies as st


class TestAsyncioRun(TestCase):

    timeout = 5

    def execute_example(self, f):
        asyncio.run(f())

    @pytest.mark.skipif(sys.version_info[:2] < (3, 7), reason="asyncio.run() is new")
    @given(st.text())
    async def test_foo(self, x):
        assume(x)
        await asyncio.sleep(0.001)
        assert x
