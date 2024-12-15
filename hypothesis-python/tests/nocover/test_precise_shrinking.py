# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import itertools
from functools import lru_cache
from random import Random
from typing import Callable, TypeVar

import pytest

from hypothesis import find, settings, strategies as st
from hypothesis.control import BuildContext
from hypothesis.errors import StopTest, UnsatisfiedAssumption
from hypothesis.internal.conjecture.data import ConjectureData, ConjectureResult, Status
from hypothesis.internal.conjecture.engine import (
    BUFFER_SIZE,
    ConjectureRunner,
    ExitReason,
    RunIsComplete,
)
from hypothesis.internal.conjecture.shrinker import sort_key as shortlex

T = TypeVar("T")


def safe_draw(data, strategy):
    with BuildContext(data):
        try:
            return data.draw(strategy)
        except UnsatisfiedAssumption:
            data.mark_invalid()


def precisely_shrink(
    strategy,
    is_interesting=lambda x: True,
    initial_condition=lambda x: True,
    end_marker=st.integers(),
    seed=0,
):
    random = Random(seed)

    while True:
        data = ConjectureData(random=random, prefix=b"", max_length=BUFFER_SIZE)
        try:
            initial_value = safe_draw(data, strategy)
        except StopTest:
            continue
        if is_interesting(initial_value) and initial_condition(initial_value):
            break

    target_check_value = safe_draw(data, end_marker)

    initial_buffer = bytes(data.buffer)

    replay = ConjectureData.for_buffer(initial_buffer)
    assert safe_draw(replay, strategy) == initial_value
    assert safe_draw(replay, end_marker) == target_check_value

    def test_function(data):
        value = safe_draw(data, strategy)
        check_value = safe_draw(data, end_marker)
        if is_interesting(value) and check_value == target_check_value:
            data.mark_interesting()

    runner = ConjectureRunner(test_function, random=random)
    try:
        buf = runner.cached_test_function(initial_buffer)
        assert buf.status == Status.INTERESTING
        assert buf.buffer == initial_buffer
        assert runner.interesting_examples
        runner.shrink_interesting_examples()
    except RunIsComplete:
        assert runner.exit_reason in (ExitReason.finished, ExitReason.max_shrinks)
    (result,) = runner.interesting_examples.values()

    data = ConjectureData.for_buffer(result.buffer)
    result_value = safe_draw(data, strategy)
    data.freeze()
    return data.as_result(), result_value


common_strategies_with_types = [
    (type(None), st.none()),
    (bool, st.booleans()),
    (bytes, st.binary()),
    (str, st.text()),
    (int, st.integers()),
]

common_strategies = [v for _, v in common_strategies_with_types]


@lru_cache
def minimal_buffer_for_strategy(s):
    return precisely_shrink(s, end_marker=st.none())[0].buffer


def test_strategy_list_is_in_sorted_order():
    assert common_strategies == sorted(
        common_strategies, key=lambda s: shortlex(minimal_buffer_for_strategy(s))
    )


@pytest.mark.parametrize("typ,strat", common_strategies_with_types)
@pytest.mark.parametrize("require_truthy", [False, True])
def test_can_precisely_shrink_values(typ, strat, require_truthy):
    if typ is type(None) and require_truthy:
        pytest.skip("None is falsey")
    if require_truthy:
        cond = bool
    else:
        cond = lambda x: True
    result, shrunk = precisely_shrink(strat, is_interesting=cond)
    assert shrunk == find(strat, cond)


alternatives = [
    comb
    for n in (2, 3, 4)
    for comb in itertools.combinations(common_strategies_with_types, n)
]

indexed_alternatives = [
    (i, j, a) for a in alternatives for i, j in itertools.combinations(range(len(a)), 2)
]


@pytest.mark.parametrize("i,j,a", indexed_alternatives)
@pytest.mark.parametrize("seed", [0, 4389048901])
def test_can_precisely_shrink_alternatives(i, j, a, seed):
    types = [u for u, _ in a]
    combined_strategy = st.one_of(*[v for _, v in a])

    result, value = precisely_shrink(
        combined_strategy,
        initial_condition=lambda x: isinstance(x, types[j]),
        is_interesting=lambda x: not any(isinstance(x, types[k]) for k in range(i)),
    )
    assert isinstance(value, types[i])


@pytest.mark.parametrize(
    "a", list(itertools.combinations(common_strategies_with_types, 3))
)
@pytest.mark.parametrize("seed", [0, 4389048901])
def test_precise_shrink_with_blocker(a, seed):
    # We're reordering this so that there is a "blocking" unusually large
    # strategy in the middle.
    x, y, z = a
    a = (x, z, y)

    types = [u for u, _ in a]
    combined_strategy = st.one_of(*[v for _, v in a])

    result, value = precisely_shrink(
        combined_strategy,
        initial_condition=lambda x: isinstance(x, types[2]),
        is_interesting=lambda x: True,
    )

    assert isinstance(value, types[0])


def find_random(
    s: st.SearchStrategy[T], condition: Callable[[T], bool], seed=None
) -> tuple[ConjectureResult, T]:
    random = Random(seed)
    while True:
        data = ConjectureData(random=random, max_length=BUFFER_SIZE, prefix=b"")
        try:
            with BuildContext(data=data):
                value = data.draw(s)
                if condition(value):
                    data.freeze()
                    return (data.as_result(), value)
        except (StopTest, UnsatisfiedAssumption):
            continue


def shrinks(strategy, buffer, *, allow_sloppy=True, seed=0):
    results = {}
    random = Random(seed)

    if allow_sloppy:

        def test_function(data):
            value = safe_draw(data, strategy)
            results[bytes(data.buffer)] = value

        runner = ConjectureRunner(test_function, settings=settings(max_examples=10**9))

        initial = runner.cached_test_function(buffer)
        try:
            runner.shrink(initial, lambda x: x.buffer == initial.buffer)
        except RunIsComplete:
            assert runner.exit_reason in (ExitReason.finished, ExitReason.max_shrinks)
    else:
        trial = ConjectureData(prefix=buffer, max_length=BUFFER_SIZE, random=random)
        with BuildContext(trial):
            trial.draw(strategy)
            assert bytes(trial.buffer) == buffer, "Buffer is already sloppy"
            padding = trial.draw_integer(0, 1000)
        initial_buffer = bytes(trial.buffer)

        def test_function(data):
            value = safe_draw(data, strategy)
            key = bytes(data.buffer)
            padding_check = data.draw_integer(0, 1000)
            if padding_check == padding:
                results[key] = value

        runner = ConjectureRunner(test_function, settings=settings(max_examples=10**9))
        initial = runner.cached_test_function(initial_buffer)
        assert len(results) == 1
        try:
            runner.shrink(initial, lambda x: x.buffer == initial_buffer)
        except RunIsComplete:
            assert runner.exit_reason in (ExitReason.finished, ExitReason.max_shrinks)

    results.pop(buffer)

    def shortlex(s):
        return (len(s), s)

    seen = set()

    result_list = []

    for k, v in sorted(results.items(), key=lambda x: shortlex(x[0])):
        if shortlex(k) < shortlex(buffer):
            t = repr(v)
            if t in seen:
                continue
            seen.add(t)
            result_list.append((k, v))
    return result_list


@pytest.mark.parametrize("a", list(itertools.product(*([common_strategies[1:]] * 2))))
@pytest.mark.parametrize("block_falsey", [False, True])
@pytest.mark.parametrize("allow_sloppy", [False, True])
@pytest.mark.parametrize("seed", [0, 2452, 99085240570])
def test_always_shrinks_to_none(a, seed, block_falsey, allow_sloppy):
    combined_strategy = st.one_of(st.none(), *a)

    result, value = find_random(combined_strategy, lambda x: x is not None)

    shrunk_values = shrinks(
        combined_strategy, result.buffer, allow_sloppy=allow_sloppy, seed=seed
    )
    assert shrunk_values[0][1] is None
