# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys
from threading import Barrier, Thread

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.internal.conjecture.junkdrawer import ensure_free_stackframes
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

pytestmark = pytest.mark.skipif(
    settings._current_profile == "crosshair", reason="crosshair is not thread safe"
)


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


def do_work():
    # arbitrary moderately-expensive work
    for x in range(500):
        _y = x**x


def test_run_different_tests_in_threads():
    @given(st.integers())
    def test1(n):
        do_work()

    @given(st.integers())
    def test2(n):
        do_work()

    thread1 = Thread(target=test1)
    thread2 = Thread(target=test2)

    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()


def test_run_given_concurrently():
    @given(st.data(), st.integers(-5, 5).map(lambda x: 10**x))
    def test(data, magnitude):
        assert magnitude != 0
        data.draw(st.complex_numbers(max_magnitude=magnitude))

    run_concurrently(test, n=2)


def test_stackframes_restores_original_recursion_limit():
    original_recursionlimit = sys.getrecursionlimit()

    def test():
        with ensure_free_stackframes():
            do_work()

            # also mix in a hypothesis test; why not.
            @given(st.integers())
            @settings(max_examples=10)
            def test(n):
                pass

            test()

    threads = []
    for _ in range(4):
        threads.append(Thread(target=test))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sys.getrecursionlimit() == original_recursionlimit
