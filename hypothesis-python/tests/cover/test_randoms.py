# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import inspect
import math
import sys
from copy import copy

import pytest

from hypothesis import HealthCheck, assume, given, settings, strategies as st
from hypothesis.internal.compat import ExceptionGroup
from hypothesis.strategies._internal.random import (
    RANDOM_METHODS,
    HypothesisRandom,
    TrueRandom,
    convert_kwargs,
    normalize_zero,
)

from tests.common.debug import assert_all_examples, find_any
from tests.common.utils import Why, xfail_on_crosshair


def test_implements_all_random_methods():
    for name in dir(HypothesisRandom):
        if not name.startswith("_") or name == "_randbelow":
            f = getattr(HypothesisRandom, name)
            if inspect.isfunction(f):
                assert f.__module__ == "hypothesis.strategies._internal.random", name


any_random = st.randoms(use_true_random=False) | st.randoms(use_true_random=True)

beta_param = st.floats(0.01, 1000)
seq_param = st.lists(st.integers(), min_size=1)


METHOD_STRATEGIES = {}


def define_method_strategy(name, **kwargs):
    METHOD_STRATEGIES[name] = kwargs


define_method_strategy("betavariate", alpha=beta_param, beta=beta_param)
define_method_strategy("binomialvariate", n=st.integers(min_value=1), p=st.floats(0, 1))
define_method_strategy("gammavariate", alpha=beta_param, beta=beta_param)
define_method_strategy("weibullvariate", alpha=beta_param, beta=beta_param)
define_method_strategy("choice", seq=seq_param)
define_method_strategy("choices", population=seq_param, k=st.integers(1, 100))
define_method_strategy("expovariate", lambd=beta_param)
define_method_strategy("_randbelow", n=st.integers(1, 2**64))
define_method_strategy("random")
define_method_strategy("getrandbits", n=st.integers(1, 128))
define_method_strategy("gauss", mu=st.floats(-1000, 1000), sigma=beta_param)
define_method_strategy("normalvariate", mu=st.floats(-1000, 1000), sigma=beta_param)
# the standard library lognormalvariate is weirdly bad at handling large floats
define_method_strategy(
    "lognormvariate", mu=st.floats(0.1, 10), sigma=st.floats(0.1, 10)
)
define_method_strategy(
    "vonmisesvariate", mu=st.floats(0, math.pi * 2), kappa=beta_param
)
# Small alpha may raise ZeroDivisionError, see https://bugs.python.org/issue41421
define_method_strategy("paretovariate", alpha=st.floats(min_value=1.0))
define_method_strategy("shuffle", x=st.lists(st.integers()))
define_method_strategy("randbytes", n=st.integers(0, 100))


INT64 = st.integers(-(2**63), 2**63 - 1)


@st.composite
def any_call_of_method(draw, method):
    if method == "sample":
        population = draw(seq_param)
        k = draw(st.integers(0, len(population)))
        kwargs = {"population": population, "k": k}
    elif method == "randint":
        a = draw(INT64)
        b = draw(INT64)
        a, b = sorted((a, b))
        kwargs = {"a": a, "b": b}
    elif method == "randrange":
        a = draw(INT64)
        b = draw(INT64)
        assume(a != b)
        a, b = sorted((a, b))
        if a == 0 and sys.version_info[:2] < (3, 10) and draw(st.booleans()):
            start = b
            stop = None
        else:
            start = a
            stop = b

        kwargs = {"start": start, "stop": stop, "step": draw(st.integers(1, 3))}
    elif method == "triangular":
        a = normalize_zero(draw(st.floats(allow_infinity=False, allow_nan=False)))
        b = normalize_zero(draw(st.floats(allow_infinity=False, allow_nan=False)))
        a, b = sorted((a, b))
        if draw(st.booleans()):
            draw(st.floats(a, b))
        kwargs = {"low": a, "high": b, "mode": None}
    elif method == "uniform":
        a = normalize_zero(draw(st.floats(allow_infinity=False, allow_nan=False)))
        b = normalize_zero(draw(st.floats(allow_infinity=False, allow_nan=False)))
        a, b = sorted((a, b))
        kwargs = {"a": a, "b": b}
    else:
        kwargs = draw(st.fixed_dictionaries(METHOD_STRATEGIES[method]))

    args, kwargs = convert_kwargs(method, kwargs)

    return (args, kwargs)


@st.composite
def any_call(draw):
    method = draw(st.sampled_from(RANDOM_METHODS))
    return (method, *draw(any_call_of_method(method)))


@pytest.mark.parametrize("method", RANDOM_METHODS)
@given(any_random, st.data())
def test_call_all_methods(method, rnd, data):
    args, kwargs = data.draw(any_call_of_method(method))
    getattr(rnd, method)(*args, **kwargs)


@given(any_random, st.integers(1, 100))
def test_rand_below(rnd, n):
    assert rnd._randbelow(n) < n


@given(any_random, beta_param, beta_param)
def test_beta_in_range(rnd, a, b):
    assert 0 <= rnd.betavariate(a, b) <= 1


def test_multiple_randoms_are_unrelated():
    @given(st.randoms(use_true_random=False), st.randoms(use_true_random=False))
    def test(r1, r2):
        assert r1.random() == r2.random()

    with pytest.raises(AssertionError):
        test()


@pytest.mark.parametrize("use_true_random", [False, True])
@given(data=st.data())
def test_randoms_can_be_synced(use_true_random, data):
    r1 = data.draw(st.randoms(use_true_random=use_true_random))
    r2 = data.draw(st.randoms(use_true_random=use_true_random))
    r2.setstate(r1.getstate())
    assert r1.random() == r2.random()


@pytest.mark.parametrize("use_true_random", [False, True])
@given(data=st.data(), method_call=any_call())
def test_seeding_to_same_value_synchronizes(use_true_random, data, method_call):
    r1 = data.draw(st.randoms(use_true_random=use_true_random))
    r2 = data.draw(st.randoms(use_true_random=use_true_random))
    method, args, kwargs = method_call
    r1.seed(0)
    r2.seed(0)
    assert getattr(r1, method)(*args, **kwargs) == getattr(r2, method)(*args, **kwargs)


@given(any_random, any_call())
def test_copying_synchronizes(r1, method_call):
    method, args, kwargs = method_call
    r2 = copy(r1)
    assert getattr(r1, method)(*args, **kwargs) == getattr(r2, method)(*args, **kwargs)


@xfail_on_crosshair(Why.symbolic_outside_context, strict=False)
@pytest.mark.parametrize("use_true_random", [True, False])
def test_seeding_to_different_values_does_not_synchronize(use_true_random):
    @given(
        st.randoms(use_true_random=use_true_random),
        st.randoms(use_true_random=use_true_random),
    )
    def test(r1, r2):
        r1.seed(0)
        r2.seed(1)
        assert r1.random() == r2.random()

    with pytest.raises(AssertionError):
        test()


@xfail_on_crosshair(Why.symbolic_outside_context, strict=False)
@pytest.mark.parametrize("use_true_random", [True, False])
def test_unrelated_calls_desynchronizes(use_true_random):
    @given(
        st.randoms(use_true_random=use_true_random),
        st.randoms(use_true_random=use_true_random),
    )
    def test(r1, r2):
        r1.seed(0)
        r2.seed(0)
        r1.randrange(1, 10)
        r2.getrandbits(128)
        assert r1.random() == r2.random()

    with pytest.raises(AssertionError):
        test()


@given(st.randoms(use_true_random=False), st.randoms(use_true_random=False))
def test_state_is_consistent(r1, r2):
    r2.setstate(r1.getstate())
    assert r1.getstate() == r2.getstate()


@given(st.randoms())
def test_does_not_use_true_random_by_default(rnd):
    assert not isinstance(rnd, TrueRandom)


@given(st.randoms(use_true_random=False))
def test_handles_singleton_uniforms_correctly(rnd):
    assert rnd.uniform(1.0, 1.0) == 1.0
    assert rnd.uniform(0.0, 0.0) == 0.0
    assert rnd.uniform(-0.0, -0.0) == 0.0
    assert rnd.uniform(0.0, -0.0) == 0.0


@given(st.randoms(use_true_random=False))
def test_handles_singleton_regions_of_triangular_correctly(rnd):
    assert rnd.triangular(1.0, 1.0) == 1.0
    assert rnd.triangular(0.0, 0.0) == 0.0
    assert rnd.triangular(-0.0, -0.0) == 0.0
    assert rnd.triangular(0.0, -0.0) == 0.0


@pytest.mark.parametrize("use_true_random", [False, True])
def test_outputs_random_calls(use_true_random):
    @given(st.randoms(use_true_random=use_true_random, note_method_calls=True))
    def test(rnd):
        rnd.uniform(0.1, 0.5)
        raise AssertionError

    with pytest.raises(AssertionError) as err:
        test()
    assert ".uniform(0.1, 0.5)" in "\n".join(err.value.__notes__)


@pytest.mark.skipif(
    "choices" not in RANDOM_METHODS,
    reason="choices not supported on this Python version",
)
@pytest.mark.parametrize("use_true_random", [False, True])
def test_converts_kwargs_correctly_in_output(use_true_random):
    @given(st.randoms(use_true_random=use_true_random, note_method_calls=True))
    def test(rnd):
        rnd.choices([1, 2, 3, 4], k=2)
        raise AssertionError

    with pytest.raises(AssertionError) as err:
        test()
    assert ".choices([1, 2, 3, 4], k=2)" in "\n".join(err.value.__notes__)


@given(st.randoms(use_true_random=False))
def test_some_ranges_are_in_range(rnd):
    assert 0 <= rnd.randrange(10) < 10
    assert 11 <= rnd.randrange(11, 20) < 20
    assert rnd.randrange(1, 100, 3) in range(1, 100, 3)
    assert rnd.randrange(100, step=3) in range(0, 100, 3)


def test_invalid_range():
    @given(st.randoms(use_true_random=False))
    def test(rnd):
        rnd.randrange(1, 1)

    with pytest.raises(ValueError):
        test()


def test_invalid_sample():
    @given(st.randoms(use_true_random=False))
    def test(rnd):
        rnd.sample([1, 2], 3)

    with pytest.raises(ValueError):
        test()


def test_triangular_modes():
    @settings(report_multiple_bugs=True)
    @given(st.randoms(use_true_random=False))
    def test(rnd):
        x = rnd.triangular(0.0, 1.0, mode=0.5)
        assert x < 0.5
        assert x > 0.5

    with pytest.raises(ExceptionGroup):
        test()


@given(st.randoms(use_true_random=False), any_call_of_method("sample"))
def test_samples_have_right_length(rnd, sample):
    (seq, k), _ = sample
    assert len(rnd.sample(seq, k)) == k


@given(st.randoms(use_true_random=False), any_call_of_method("choices"))
def test_choices_have_right_length(rnd, choices):
    args, kwargs = choices

    seq = args[0]
    k = kwargs.get("k", 1)
    assert len(rnd.choices(seq, k=k)) == k


@given(any_random, st.integers(0, 100))
def test_randbytes_have_right_length(rnd, n):
    assert len(rnd.randbytes(n)) == n


@pytest.mark.skipif(
    settings._current_profile == "crosshair",
    reason="takes hours; may get faster after https://github.com/pschanely/CrossHair/issues/332",
)
@given(any_random)
def test_can_manage_very_long_ranges_with_step(rnd):
    i = rnd.randrange(0, 2**256, 3)

    assert i % 3 == 0
    assert 0 <= i < 2**256
    assert i in range(0, 2**256, 3)


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(any_random, st.data())
def test_range_with_arbitrary_step_is_in_range(rnd, data):
    endpoints = st.integers(-100, 100)
    step = data.draw(st.integers(1, 3))
    start, stop = sorted((data.draw(endpoints), data.draw(endpoints)))
    assume(start < stop)
    i = rnd.randrange(start, stop, step)
    assert i in range(start, stop, step)


@given(any_random, st.integers(min_value=1))
def test_range_with_only_stop(rnd, n):
    assert 0 <= rnd.randrange(n) < n


def test_can_find_end_of_range():
    find_any(
        st.randoms(use_true_random=False).map(lambda r: r.randrange(0, 11, 2)),
        lambda n: n == 10,
    )
    find_any(
        st.randoms(use_true_random=False).map(lambda r: r.randrange(0, 10, 2)),
        lambda n: n == 8,
    )


@given(st.randoms(use_true_random=False))
def test_can_sample_from_whole_range(rnd):
    xs = list(map(str, range(10)))
    ys = rnd.sample(xs, len(xs))
    assert sorted(ys) == sorted(xs)


@given(st.randoms(use_true_random=False))
def test_can_sample_from_large_subset(rnd):
    xs = list(map(str, range(10)))
    n = len(xs) // 3
    ys = rnd.sample(xs, n)
    assert set(ys).issubset(set(xs))
    assert len(ys) == len(set(ys)) == n


@given(st.randoms(use_true_random=False))
def test_can_draw_empty_from_empty_sequence(rnd):
    assert rnd.sample([], 0) == []


def test_random_includes_zero_excludes_one():
    strat = st.randoms(use_true_random=False).map(lambda r: r.random())
    assert_all_examples(strat, lambda x: 0 <= x < 1)
    find_any(strat, lambda x: x == 0)


def test_betavariate_includes_zero_and_one():
    # https://github.com/HypothesisWorks/hypothesis/issues/4297#issuecomment-2720144709
    strat = st.randoms(use_true_random=False).flatmap(
        lambda r: st.builds(
            r.betavariate, alpha=st.just(1.0) | beta_param, beta=beta_param
        )
    )
    assert_all_examples(strat, lambda x: 0 <= x <= 1)
    find_any(strat, lambda x: x == 0)
    find_any(strat, lambda x: x == 1)
