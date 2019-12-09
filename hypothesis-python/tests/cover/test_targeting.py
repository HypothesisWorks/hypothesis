# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

from operator import itemgetter

import pytest

from hypothesis import Phase, example, given, seed, settings, strategies as st, target
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import string_types


@example(0.0, "this covers the branch where context.data is None")
@given(observation=st.floats(allow_nan=False, allow_infinity=False), label=st.text())
def test_allowed_inputs_to_target(observation, label):
    target(observation, label)


@given(
    observation=st.floats(min_value=1, allow_nan=False, allow_infinity=False),
    label=st.sampled_from(["a", "few", "labels"]),
)
def test_allowed_inputs_to_target_fewer_labels(observation, label):
    target(observation, label)


@given(st.floats(min_value=1, max_value=10))
def test_target_without_label(observation):
    target(observation)


@given(
    st.lists(
        st.tuples(st.floats(allow_nan=False, allow_infinity=False), st.text()),
        min_size=1,
        unique_by=itemgetter(1),
    )
)
def test_multiple_target_calls(args):
    for observation, label in args:
        target(observation, label)


@given(
    st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=11, max_size=20)
)
def test_respects_max_pool_size(observations):
    """Using many examples of several labels like this stresses the
    pool-size logic and internal assertions in TargetSelector.
    """
    for i, obs in enumerate(observations):
        target(obs, label=str(i))


def everything_except(type_):
    # Note: we would usually stick to fater traditional or parametrized
    # tests to check that invalid inputs are rejected, but for `target()`
    # we need to use `@given` (to validate arguments instead of context)
    # so we might as well apply this neat recipe.
    return (
        st.from_type(type)
        .flatmap(st.from_type)
        .filter(lambda x: not isinstance(x, type_))
    )


@example(float("nan"), "")
@example(float("inf"), "")
@example(float("-inf"), "")
@example("1", "Non-float observations are invalid")
@example(0.0, ["a list of strings is not a valid label"])
@given(observation=everything_except(float), label=everything_except(string_types))
def test_disallowed_inputs_to_target(observation, label):
    with pytest.raises(InvalidArgument):
        target(observation, label)


def test_cannot_target_outside_test():
    with pytest.raises(InvalidArgument):
        target(1.0, "example label")


@given(st.none())
def test_cannot_target_same_label_twice(_):
    target(0.0, label="label")
    with pytest.raises(InvalidArgument):
        target(1.0, label="label")


@given(st.none())
def test_cannot_target_default_label_twice(_):
    target(0.0)
    with pytest.raises(InvalidArgument):
        target(1.0)


@given(st.lists(st.integers()), st.none())
def test_targeting_with_following_empty(ls, n):
    # This exercises some logic in the optimiser that prevents it from trying
    # to mutate empty examples at the end of the test case.
    target(float(len(ls)))


@given(
    st.tuples(
        *([st.none()] * 10 + [st.integers()] + [st.none()] * 10 + [st.integers()])
    )
)
def test_targeting_with_many_empty(_):
    # This exercises some logic in the optimiser that prevents it from trying
    # to mutate empty examples in the middle of the test case.
    target(1.0)


def test_targeting_increases_max_length():
    strat = st.lists(st.booleans())

    @settings(database=None, max_examples=200, phases=[Phase.generate, Phase.target])
    @given(strat)
    def test_with_targeting(ls):
        target(float(len(ls)))
        assert len(ls) <= 100

    with pytest.raises(AssertionError):
        test_with_targeting()


def test_targeting_can_be_disabled():
    strat = st.lists(st.integers(0, 255))

    def score(enabled):
        result = [0]
        phases = [Phase.generate]
        if enabled:
            phases.append(Phase.target)

        @seed(0)
        @settings(database=None, max_examples=200, phases=phases)
        @given(strat)
        def test(ls):
            score = float(sum(ls))
            result[0] = max(result[0], score)
            target(score)

        test()
        return result[0]

    assert score(enabled=True) > score(enabled=False)
