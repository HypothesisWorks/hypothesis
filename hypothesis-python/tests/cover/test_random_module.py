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
import random

import pytest

from hypothesis import (
    Phase,
    core,
    find,
    given,
    register_random,
    settings,
    strategies as st,
)
from hypothesis.errors import HypothesisWarning, InvalidArgument
from hypothesis.internal import entropy
from hypothesis.internal.compat import GRAALPY, PYPY
from hypothesis.internal.entropy import deterministic_PRNG


def gc_collect():
    # CPython uses reference counting, so objects (without circular refs)
    # are collected immediately on `del`, breaking weak references.
    # Python implementations with other garbage collection strategies may
    # or may not, so we use this function in tests before counting the
    # surviving references to ensure that they're deterministic.
    if PYPY or GRAALPY:
        gc.collect()


def test_can_seed_random():
    @settings(phases=(Phase.generate, Phase.shrink))
    @given(st.random_module())
    def test(r):
        raise AssertionError

    with pytest.raises(AssertionError) as err:
        test()
    assert "RandomSeeder(0)" in "\n".join(err.value.__notes__)


@given(st.random_module(), st.random_module())
def test_seed_random_twice(r, r2):
    assert repr(r) == repr(r2)


@given(st.random_module())
def test_does_not_fail_health_check_if_randomness_is_used(r):
    random.getrandbits(128)


def test_cannot_register_non_Random():
    with pytest.raises(InvalidArgument):
        register_random("not a Random instance")


@pytest.mark.filterwarnings(
    "ignore:It looks like `register_random` was passed an object that could be garbage collected"
)
def test_registering_a_Random_is_idempotent():
    gc_collect()
    n_registered = len(entropy.RANDOMS_TO_MANAGE)
    r = random.Random()
    register_random(r)
    register_random(r)
    assert len(entropy.RANDOMS_TO_MANAGE) == n_registered + 1
    del r
    gc_collect()
    assert len(entropy.RANDOMS_TO_MANAGE) == n_registered


def test_manages_registered_Random_instance():
    r = random.Random()
    register_random(r)
    state = r.getstate()
    result = []

    @given(st.integers())
    def inner(x):
        v = r.random()
        if result:
            assert v == result[0]
        else:
            result.append(v)

    inner()
    assert state == r.getstate()


def test_registered_Random_is_seeded_by_random_module_strategy():
    r = random.Random()
    register_random(r)
    state = r.getstate()
    results = set()
    count = 0

    @given(st.integers())
    def inner(x):
        nonlocal count
        results.add(r.random())
        count += 1

    inner()
    assert count > len(results) * 0.9, "too few unique random numbers"
    assert state == r.getstate()


@given(st.random_module())
def test_will_actually_use_the_random_seed(rnd):
    a = random.randint(0, 100)
    b = random.randint(0, 100)
    random.seed(rnd.seed)
    assert a == random.randint(0, 100)
    assert b == random.randint(0, 100)


def test_given_does_not_pollute_state():
    with deterministic_PRNG():

        @given(st.random_module())
        def test(r):
            pass

        test()
        state_a = random.getstate()
        state_a2 = core._hypothesis_global_random.getstate()

        test()
        state_b = random.getstate()
        state_b2 = core._hypothesis_global_random.getstate()

        assert state_a == state_b
        assert state_a2 != state_b2


def test_find_does_not_pollute_state():
    with deterministic_PRNG():
        find(st.random_module(), lambda r: True)
        state_a = random.getstate()
        state_a2 = core._hypothesis_global_random.getstate()

        find(st.random_module(), lambda r: True)
        state_b = random.getstate()
        state_b2 = core._hypothesis_global_random.getstate()

        assert state_a == state_b
        assert state_a2 != state_b2


@pytest.mark.filterwarnings(
    "ignore:It looks like `register_random` was passed an object that could be garbage collected"
)
def test_evil_prng_registration_nonsense():
    # my guess is that other tests may register randoms that are then marked for
    # deletion (but not actually gc'd yet). Therefore, depending on the order tests
    # are run, RANDOMS_TO_MANAGE may start with more entries than after a gc. To
    # force a clean slate for this test, unconditionally gc.
    gc.collect()
    # The first test to call deterministic_PRNG registers a new random instance.
    # If that's this test, it will throw off our n_registered count in the middle.
    # start with a no-op to ensure this registration has occurred.
    with deterministic_PRNG(0):
        pass

    n_registered = len(entropy.RANDOMS_TO_MANAGE)
    r1, r2, r3 = random.Random(1), random.Random(2), random.Random(3)
    s2 = r2.getstate()

    # We're going to be totally evil here: register two randoms, then
    # drop one and add another, and finally check that we reset only
    # the states that we collected before we started
    register_random(r1)
    k = max(entropy.RANDOMS_TO_MANAGE)  # get a handle to check if r1 still exists
    register_random(r2)
    assert len(entropy.RANDOMS_TO_MANAGE) == n_registered + 2

    with deterministic_PRNG(0):
        del r1
        gc_collect()
        assert k not in entropy.RANDOMS_TO_MANAGE, "r1 has been garbage-collected"
        assert len(entropy.RANDOMS_TO_MANAGE) == n_registered + 1

        r2.seed(4)
        register_random(r3)
        r3.seed(4)
        s4 = r3.getstate()

    # Implicit check, no exception was raised in __exit__
    assert r2.getstate() == s2, "reset previously registered random state"
    assert r3.getstate() == s4, "retained state when registered within the context"


@pytest.mark.skipif(
    PYPY, reason="We can't guard against bad no-reference patterns in pypy."
)
def test_passing_unreferenced_instance_raises():
    with pytest.raises(ReferenceError):
        register_random(random.Random(0))


@pytest.mark.skipif(
    PYPY, reason="We can't guard against bad no-reference patterns in pypy."
)
def test_passing_unreferenced_instance_within_function_scope_raises():
    def f():
        register_random(random.Random(0))

    with pytest.raises(ReferenceError):
        f()


@pytest.mark.skipif(
    PYPY, reason="We can't guard against bad no-reference patterns in pypy."
)
def test_passing_referenced_instance_within_function_scope_warns():
    def f():
        r = random.Random(0)
        register_random(r)

    with pytest.warns(
        HypothesisWarning,
        match="It looks like `register_random` was passed an object that could be"
        " garbage collected",
    ):
        f()


@pytest.mark.filterwarnings(
    "ignore:It looks like `register_random` was passed an object that could be garbage collected"
)
@pytest.mark.skipif(
    PYPY, reason="We can't guard against bad no-reference patterns in pypy."
)
def test_register_random_within_nested_function_scope():
    n_registered = len(entropy.RANDOMS_TO_MANAGE)

    def f():
        r = random.Random()
        register_random(r)
        assert len(entropy.RANDOMS_TO_MANAGE) == n_registered + 1

    f()
    gc_collect()
    assert len(entropy.RANDOMS_TO_MANAGE) == n_registered
