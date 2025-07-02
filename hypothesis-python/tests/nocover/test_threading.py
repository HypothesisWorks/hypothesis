# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from threading import Barrier, Thread

import pytest

from hypothesis import given, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule


def run_concurrently(function, n: int) -> None:
    def run():
        barrier.wait()
        function()

    threads = [Thread(target=run) for _ in range(n)]
    barrier = Barrier(n)

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()


def test_can_run_given_in_thread():
    has_run_successfully = False

    @given(st.integers())
    def test(n):
        nonlocal has_run_successfully
        has_run_successfully = True

    t = Thread(target=test)
    t.start()
    t.join()
    assert has_run_successfully


@pytest.mark.xfail(reason="hypothesis not yet thread-safe", strict=False)
def test_run_stateful_test_concurrently():
    class MyStateMachine(RuleBasedStateMachine):
        def __init__(self):
            super().__init__()

        @rule(n=st.integers())
        def my_rule(self, n):
            pass

        @invariant()
        def my_invariant(self):
            pass

    TestMyStateful = MyStateMachine.TestCase().runTest
    run_concurrently(TestMyStateful, n=2)
