# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import gc
import math
import sys
import time

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.errors import DeadlineExceeded, Flaky, InvalidArgument
from hypothesis.internal.conjecture import junkdrawer
from hypothesis.internal.observability import TESTCASE_CALLBACKS

from tests.common.utils import assert_falsifying_output, fails_with


def test_raises_deadline_on_slow_test():
    @settings(deadline=500)
    @given(st.integers())
    def slow(i):
        time.sleep(1)

    with pytest.raises(DeadlineExceeded):
        slow()


@fails_with(DeadlineExceeded)
@given(st.integers())
def test_slow_tests_are_errors_by_default(i):
    time.sleep(1)


def test_non_numeric_deadline_is_an_error():
    with pytest.raises(InvalidArgument):
        settings(deadline="3 seconds")


@given(st.integers())
@settings(deadline=None)
def test_slow_with_none_deadline(i):
    time.sleep(1)


def test_raises_flaky_if_a_test_becomes_fast_on_rerun():
    once = [True]

    @settings(deadline=500)
    @given(st.integers())
    def test_flaky_slow(i):
        if once[0]:
            once[0] = False
            time.sleep(1)

    with pytest.raises(Flaky):
        test_flaky_slow()


def test_deadlines_participate_in_shrinking():
    @settings(deadline=500, max_examples=1000)
    @given(st.integers(min_value=0))
    def slow_if_large(i):
        if i >= 1000:
            time.sleep(1)

    assert_falsifying_output(
        slow_if_large,
        expected_exception=DeadlineExceeded,
        i=1000,
    )


def test_keeps_you_well_above_the_deadline():
    seen = set()
    failed_once = [False]

    @settings(deadline=100)
    @given(st.integers(0, 2000))
    def slow(i):
        # Make sure our initial failure isn't something that immediately goes
        # flaky.
        if not failed_once[0]:
            if i * 0.9 <= 100:
                return
            else:
                failed_once[0] = True

        t = i / 1000
        if i in seen:
            time.sleep(0.9 * t)
        else:
            seen.add(i)
            time.sleep(t)

    with pytest.raises(DeadlineExceeded):
        slow()


def test_gives_a_deadline_specific_flaky_error_message():
    once = [True]

    @settings(deadline=100)
    @given(st.integers())
    def slow_once(i):
        if once[0]:
            once[0] = False
            time.sleep(0.2)

    with pytest.raises(Flaky) as err:
        slow_once()
    assert "Unreliable test timing" in "\n".join(err.value.__notes__)
    assert "took 2" in "\n".join(err.value.__notes__)


@pytest.mark.parametrize("slow_strategy", [False, True])
@pytest.mark.parametrize("slow_test", [False, True])
def test_should_only_fail_a_deadline_if_the_test_is_slow(slow_strategy, slow_test):
    s = st.integers()
    if slow_strategy:
        s = s.map(lambda x: time.sleep(0.08))

    @settings(deadline=50)
    @given(st.data())
    def test(data):
        data.draw(s)
        if slow_test:
            time.sleep(0.1)

    if slow_test:
        with pytest.raises(DeadlineExceeded):
            test()
    else:
        test()


@pytest.mark.skipif(not hasattr(gc, "callbacks"), reason="CPython specific gc delay")
def test_should_not_fail_deadline_due_to_gc():
    @settings(max_examples=1, deadline=50)
    @given(st.integers())
    def test(i):
        before = time.perf_counter()
        gc.collect()
        assert time.perf_counter() - before >= 0.1  # verify that we're slow

    def delay(phase, _info):
        if phase == "start":
            time.sleep(0.1)

    try:
        gc.callbacks.append(delay)
        test()
    finally:
        gc.callbacks.remove(delay)


@pytest.mark.skipif(not hasattr(gc, "callbacks"), reason="PyPy has weird stack-limit behaviour")
def test_gc_hooks_do_not_cause_unraisable_recursionerror():
    # We were concerned in #3979 that we might see bad results from a RecursionError
    # inside the GC hook, if the stack was already deep and someone (e.g. Pytest)
    # had installed a sys.unraisablehook which raises that later.

    NUM_CYCLES = 10_000

    def probe_depth():
        try:
            return probe_depth() + 1
        except RecursionError:
            return 0

    def at_depth(depth, fn):
        if depth <= 1:
            return fn()
        else:
            # Recurse towards requested depth
            return at_depth(depth - 1, fn)

    def gen_cycles():
        # We may be at the recursion limit, no free stack frames. Generate lots
        # of reference cycles. Beware: there may not even be room for raising new
        # exceptions here, anything will end up as a RecursionError.
        for i in range(NUM_CYCLES):
            a = [None]
            b = [a]
            a[0] = b

    def gen_cycles_at_depth(depth, *, gc_disable):
        try:
            if gc_disable:
                gc.disable()
            at_depth(depth, gen_cycles)
            if gc_disable:
                assert gc.collect() >= 2 * NUM_CYCLES
            else:
                assert gc.collect() < 2 * NUM_CYCLES  # collection was triggered
        finally:
            gc.enable()

    @given(st.booleans())
    def inner_test(_):
        max_depth = probe_depth()  # would have to be called twice on PyPy

        # Lower the limit to where we can successfully generate cycles
        while True:
            try:
                gen_cycles_at_depth(max_depth, gc_disable=True)
            except RecursionError:
                max_depth -= 1
            else:
                break

        # Verify limits w/o any gc interfering
        gen_cycles_at_depth(max_depth - 1, gc_disable=True)  # this line raises RecursionError on Pypy
        gen_cycles_at_depth(max_depth, gc_disable=True)  # while this line doesn't
        with pytest.raises(RecursionError):
            gen_cycles_at_depth(max_depth + 1, gc_disable=True)

        # Check that the limit is unchanged with gc enabled
        gen_cycles_at_depth(max_depth - 1, gc_disable=False)
        gen_cycles_at_depth(max_depth, gc_disable=False)
        with pytest.raises(RecursionError):
            gen_cycles_at_depth(max_depth + 1, gc_disable=False)

    inner_test()
