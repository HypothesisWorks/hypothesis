# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import HealthCheck, given, settings, strategies as st

from tests.common.debug import assert_all_examples, find_any, minimal

use_several_sizes = pytest.mark.parametrize("size", [1, 2, 5, 10, 100, 1000])


@use_several_sizes
def test_stop_stays_within_bounds(size):
    assert_all_examples(
        st.slices(size),
        lambda x: x.stop is None or (x.stop >= -size and x.stop <= size),
    )


@use_several_sizes
def test_start_stay_within_bounds(size):
    assert_all_examples(
        st.slices(size).filter(lambda x: x.start is not None),
        lambda x: range(size)[x.start] or True,  # no IndexError raised
    )


@use_several_sizes
def test_step_stays_within_bounds(size):
    # indices -> (start, stop, step)
    # Stop is exclusive so we use -1 as the floor.
    # This uses the indices that slice produces to make this test more readable
    # due to how splice processes None being a little complex
    assert_all_examples(
        st.slices(size),
        lambda x: (
            x.indices(size)[0] + x.indices(size)[2] <= size
            and x.indices(size)[0] + x.indices(size)[2] >= -size
        )
        or x.start % size == x.stop % size,
    )


@use_several_sizes
def test_step_will_not_be_zero(size):
    assert_all_examples(st.slices(size), lambda x: x.step != 0)


@use_several_sizes
def test_slices_will_shrink(size):
    sliced = minimal(st.slices(size))
    assert sliced.start == 0 or sliced.start is None
    assert sliced.stop == 0 or sliced.stop is None
    assert sliced.step is None


@given(st.integers(1, 1000))
@settings(deadline=None, suppress_health_check=list(HealthCheck))
def test_step_will_be_negative(size):
    find_any(st.slices(size), lambda x: (x.step or 1) < 0)


@given(st.integers(1, 1000))
@settings(deadline=None)
def test_step_will_be_positive(size):
    find_any(st.slices(size), lambda x: (x.step or 1) > 0)


@pytest.mark.parametrize("size", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
def test_stop_will_equal_size(size):
    find_any(st.slices(size), lambda x: x.stop == size, settings(max_examples=10**6))


@pytest.mark.parametrize("size", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
def test_start_will_equal_size(size):
    find_any(
        st.slices(size), lambda x: x.start == size - 1, settings(max_examples=10**6)
    )


@given(st.integers(1, 1000))
@settings(deadline=None)
def test_start_will_equal_0(size):
    find_any(st.slices(size), lambda x: x.start == 0)


@given(st.integers(1, 1000))
@settings(deadline=None)
def test_start_will_equal_stop(size):
    find_any(st.slices(size), lambda x: x.start == x.stop)


def test_size_is_equal_0():
    assert_all_examples(
        st.slices(0), lambda x: x.step != 0 and x.start is None and x.stop is None
    )
