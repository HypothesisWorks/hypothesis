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
import time
from threading import Barrier, Thread

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.errors import DeadlineExceeded, InvalidArgument
from hypothesis.internal.conjecture.junkdrawer import ensure_free_stackframes
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule
from hypothesis.strategies import SearchStrategy

from tests.common.debug import check_can_generate_examples
from tests.common.utils import run_concurrently

pytestmark = pytest.mark.skipif(
    settings._current_profile == "crosshair", reason="crosshair is not thread safe"
)


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


def do_work(*, multiplier=1):
    # arbitrary moderately-expensive work
    for x in range(500 * multiplier):
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
        thread.join(timeout=10)

    assert sys.getrecursionlimit() == original_recursionlimit


@pytest.mark.parametrize(
    "strategy",
    [
        st.recursive(st.none(), st.lists, max_leaves=-1),
        st.recursive(st.none(), st.lists, max_leaves=0),
        st.recursive(st.none(), st.lists, max_leaves=1.0),
    ],
)
def test_handles_invalid_args_cleanly(strategy):
    # we previously had a race in SearchStrategy.validate, where one thread would
    # set `validate_called = True` (which it has to do first for recursive
    # strategies), then another thread would try to generate before the validation
    # finished and errored, and would get into weird technically-valid states
    # like interpreting 1.0 as 1. I saw FlakyStrategyDefinition here because the
    # validating + errored thread drew zero choices, but the other thread drew
    # 1 choice, for the same shared strategy.

    def check():
        with pytest.raises(InvalidArgument):
            check_can_generate_examples(strategy)

    run_concurrently(check, n=4)


def test_single_thread_can_raise_deadline_exceeded():
    # a slow test running inside a thread, but not concurrently, should still
    # be able to raise DeadlineExceeded.
    @given(st.integers())
    @settings(max_examples=5)
    def slow_test(n):
        do_work()
        time.sleep(0.4)

    def target():
        with pytest.raises(DeadlineExceeded):
            slow_test()

    thread = Thread(target=target)
    thread.start()
    thread.join(timeout=10)


def test_deadline_exceeded_not_raised_under_concurrent_threads():
    # it's still possible for multithreaded calls to a slow function to raise
    # DeadlineExceeded, if the first thread completes its entire test before
    # any other thread starts. For this test, prevent this scenario with a barrier,
    # forcing the threads to run in parallel.
    n_threads = 8
    barrier = Barrier(n_threads)

    @given(st.integers())
    @settings(max_examples=5)
    def slow_test(n):
        do_work()
        time.sleep(0.4)
        barrier.wait()

    run_concurrently(slow_test, n=n_threads)


def test_deadline_exceeded_can_be_raised_after_threads():
    # if we had concurrent threads before, but they've finished now, we should
    # still be able to raise DeadlineExceeded normally. Importantly, we test this
    # for the same test as was running before, since concurrent thread use is
    # tracked per-@given.

    @given(st.integers())
    @settings(max_examples=5)
    def slow_test(n):
        do_work()
        if should_sleep:
            time.sleep(0.4)

    should_sleep = False
    run_concurrently(slow_test, n=8)

    should_sleep = True
    with pytest.raises(DeadlineExceeded):
        slow_test()


def test_one_of_branches_lock():
    class SlowBranchesStrategy(SearchStrategy):
        @property
        def branches(self):
            # multiplier=2 reproduces more consistently than multiplier=1 for me
            do_work(multiplier=2)
            return [st.integers(), st.text()]

    branch_counts = set()
    s = st.one_of(SlowBranchesStrategy(), SlowBranchesStrategy())

    def test():
        branches = len(s.branches)
        branch_counts.add(branches)

    run_concurrently(test, n=10)
    assert len(branch_counts) == 1
    # there are 4 independent strategies, but only 2 distinct ones -
    # st.integers(), and st.text().
    assert branch_counts == {2}
