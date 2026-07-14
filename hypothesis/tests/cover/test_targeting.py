# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from operator import itemgetter

import pytest

from hypothesis import example, given, strategies as st, target
from hypothesis.control import current_build_context
from hypothesis.errors import InvalidArgument


@example(0.0, "this covers the branch where context.data is None")
@given(
    observation=st.integers() | st.floats(allow_nan=False, allow_infinity=False),
    label=st.text(),
)
def test_allowed_inputs_to_target(observation, label):
    target(observation, label=label)


@given(
    observation=st.integers(min_value=1)
    | st.floats(min_value=1, allow_nan=False, allow_infinity=False),
    label=st.sampled_from(["a", "few", "labels"]),
)
def test_allowed_inputs_to_target_fewer_labels(observation, label):
    target(observation, label=label)


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
        target(observation, label=label)


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
    # Note: we would usually stick to faster traditional or parametrized
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
@given(observation=everything_except((float, int)), label=everything_except(str))
def test_disallowed_inputs_to_target(observation, label):
    with pytest.raises(InvalidArgument):
        target(observation, label=label)


def test_cannot_target_outside_test():
    with pytest.raises(InvalidArgument):
        target(1.0, label="example label")


@given(st.none())
def test_cannot_target_same_label_twice(_):
    if current_build_context().data.provider.avoid_realization:
        pytest.skip("target() is a noop to avoid realizing arguments")
    target(0.0, label="label")
    with pytest.raises(InvalidArgument):
        target(1.0, label="label")


@given(st.none())
def test_cannot_target_default_label_twice(_):
    target(0.0)
    with pytest.raises(InvalidArgument):
        target(1.0)
