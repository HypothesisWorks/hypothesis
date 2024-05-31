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
import sys
import threading
import warnings

import pytest

from hypothesis import HealthCheck, given, settings, strategies as st

from tests.common.debug import find_any, minimal
from tests.common.utils import flaky


def test_can_generate_with_large_branching():
    def flatten(x):
        if isinstance(x, list):
            return sum(map(flatten, x), [])
        else:
            return [x]

    size = 20

    xs = minimal(
        st.recursive(
            st.integers(),
            lambda x: st.lists(x, min_size=size // 2),
            max_leaves=size * 2,
        ),
        lambda x: isinstance(x, list) and len(flatten(x)) >= size,
        timeout_after=None,
    )
    assert flatten(xs) == [0] * size


def test_can_generate_some_depth_with_large_branching():
    def depth(x):
        if x and isinstance(x, list):
            return 1 + max(map(depth, x))
        else:
            return 1

    xs = minimal(
        st.recursive(st.integers(), st.lists),
        lambda x: depth(x) > 1,
        timeout_after=None,
    )
    assert xs in ([0], [[]])


def test_can_find_quite_broad_lists():
    def breadth(x):
        if isinstance(x, list):
            return sum(map(breadth, x))
        else:
            return 1

    target = 10

    broad = minimal(
        st.recursive(st.booleans(), lambda x: st.lists(x, max_size=target // 2)),
        lambda x: breadth(x) >= target,
        settings=settings(max_examples=10000),
        timeout_after=None,
    )
    assert breadth(broad) == target


def test_drawing_many_near_boundary():
    target = 4

    ls = minimal(
        st.lists(
            st.recursive(
                st.booleans(),
                lambda x: st.lists(
                    x, min_size=2 * (target - 1), max_size=2 * target
                ).map(tuple),
                max_leaves=2 * target - 1,
            )
        ),
        lambda x: len(set(x)) >= target,
        timeout_after=None,
    )
    assert len(ls) == target


def test_can_use_recursive_data_in_sets():
    nested_sets = st.recursive(st.booleans(), st.frozensets, max_leaves=3)
    find_any(nested_sets, settings=settings(deadline=None))

    def flatten(x):
        if isinstance(x, bool):
            return frozenset((x,))
        else:
            result = frozenset()
            for t in x:
                result |= flatten(t)
                if len(result) == 2:
                    break
            return result

    x = minimal(nested_sets, lambda x: len(flatten(x)) == 2, settings(deadline=None))
    assert x in (
        frozenset((False, True)),
        frozenset((False, frozenset((True,)))),
        frozenset((frozenset((False, True)),)),
    )


@flaky(max_runs=2, min_passes=1)
def test_can_form_sets_of_recursive_data():
    size = 3

    trees = st.sets(
        st.recursive(
            st.booleans(),
            lambda x: st.lists(x, min_size=size).map(tuple),
            max_leaves=20,
        )
    )
    xs = minimal(trees, lambda x: len(x) >= size, timeout_after=None)
    assert len(xs) == size


def test_drawing_from_recursive_strategy_is_thread_safe():
    shared_strategy = st.recursive(
        st.integers(), lambda s: st.lists(s, max_size=2), max_leaves=20
    )

    errors = []

    @settings(
        database=None, deadline=None, suppress_health_check=[HealthCheck.too_slow]
    )
    @given(data=st.data())
    def test(data):
        try:
            data.draw(shared_strategy)
        except Exception as exc:
            errors.append(exc)

    threads = []

    original_recursionlimit = sys.getrecursionlimit()

    # We may get a warning here about not resetting recursionlimit,
    # since it was changed during execution; ignore it.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        for _ in range(4):
            threads.append(threading.Thread(target=test))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    # Cleanup: reset the recursion limit that was (probably) not reset
    # automatically in the threaded test.
    sys.setrecursionlimit(original_recursionlimit)

    assert not errors


SELF_REF = st.recursive(
    st.deferred(lambda: st.booleans() | SELF_REF),
    lambda s: st.lists(s, min_size=1),
)


@settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
@given(SELF_REF)
def test_self_ref_regression(_):
    # See https://github.com/HypothesisWorks/hypothesis/issues/2794
    pass


@flaky(min_passes=1, max_runs=2)
def test_gc_hooks_do_not_cause_unraisable_recursionerror():
    # We were concerned in #3979 that we might see bad results from a RecursionError
    # inside the GC hook, if the stack was already deep and someone (e.g. Pytest)
    # had installed a sys.unraisablehook which raises that later.

    # This test is potentially flaky, because the stack usage of a function is not
    # constant. Regardless, if the test passes just once that's sufficient proof that
    # it's not the GC (or accounting of it) that is at fault.

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
        # of reference cycles, to trigger GC (if enabled). Beware: there may not
        # even be room for raising new exceptions here, anything will end up as
        # a RecursionError.
        for _ in range(NUM_CYCLES):
            a = [None]
            b = [a]
            a[0] = b

    def gen_cycles_at_depth(depth, *, gc_disable):
        try:
            if gc_disable:
                gc.disable()
            at_depth(depth, gen_cycles)
            dead_objects = gc.collect()
            if dead_objects is not None:  # == None on PyPy
                if gc_disable:
                    assert dead_objects >= 2 * NUM_CYCLES
                else:
                    assert dead_objects < 2 * NUM_CYCLES  # collection was triggered
        finally:
            gc.enable()

    @given(st.booleans())
    def inner_test(_):
        max_depth = probe_depth()
        max_depth = probe_depth()  # Executing probe twice de-flakes PyPy

        while True:
            # Lower the limit to where we can successfully generate cycles
            try:
                gen_cycles_at_depth(max_depth, gc_disable=True)
            except RecursionError:
                max_depth -= 1
            else:
                break

        # Verify limits w/o any gc interfering

        # gen_cycles_at_depth(max_depth - 1, gc_disable=True)  # RecursionError on PyPy (!)
        gen_cycles_at_depth(max_depth, gc_disable=True)
        with pytest.raises(RecursionError):
            gen_cycles_at_depth(max_depth + 1, gc_disable=True)

        # Check that the limit is unchanged with gc enabled

        gen_cycles_at_depth(max_depth, gc_disable=False)
        with pytest.raises(RecursionError):
            gen_cycles_at_depth(max_depth + 1, gc_disable=False)

    inner_test()
