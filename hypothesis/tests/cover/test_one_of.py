# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re
import string
from collections.abc import Sequence

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.errors import InvalidArgument

from tests.common.debug import assert_no_examples


def test_one_of_empty():
    e = st.one_of()
    assert e.is_empty
    assert_no_examples(e)


@given(st.one_of(st.integers().filter(bool)))
def test_one_of_filtered(i):
    assert bool(i)


@given(st.one_of(st.just(100).flatmap(st.integers)))
def test_one_of_flatmapped(i):
    assert i >= 100


def test_one_of_single_strategy_is_noop():
    s = st.integers()
    assert st.one_of(s) is s
    assert st.one_of([s]) is s


def test_one_of_without_strategies_suggests_sampled_from():
    with pytest.raises(
        InvalidArgument,
        match=re.escape("Did you mean st.sampled_from([1, 2, 3])?"),
    ):
        st.one_of(1, 2, 3)


@pytest.mark.parametrize(
    "strategy, count",
    [
        (st.one_of(st.integers(), st.integers(), st.integers()), 1),
        (st.one_of(st.integers(), st.one_of(st.integers(), st.integers())), 2),
        ((st.integers() | st.integers()) | st.integers(), 1),
        (st.integers() | (st.integers() | st.integers()), 1),
        (st.integers() | st.text() | st.booleans(), 1),
        (st.from_type(int | Sequence[int]), 2),
    ],
)
def test_one_of_unwrapping(strategy, count):
    assert repr(strategy).count("one_of(") == count


def test_shrinking_mixed_alphabet_one_of_does_not_crash():
    # If a shrinking pass proposes a string value outside the intervals of the
    # one_of branch it is copied onto, cached_test_function used to compute
    # sort_key(nodes) - which indexes every character in its node's interval
    # set - before discarding the invalid attempt, raising
    # "ValueError: <n> is not in list" from intervalsets.index instead of
    # reporting the shrunk failure (issue #4905).
    @st.composite
    def lines(draw):
        parts = draw(
            st.lists(
                st.one_of(
                    st.text("-=_*~ ", min_size=1, max_size=40),
                    st.text(" \t", max_size=3),
                    st.text(
                        string.ascii_letters
                        + string.digits
                        + string.punctuation
                        + " \t\xa0",
                        max_size=50,
                    ),
                ),
                max_size=6,
            )
        )
        return "\n".join(parts)

    @settings(database=None, derandomize=True, max_examples=100)
    @given(lines())
    def test(t):
        for w in t.split():
            letters = "".join(c for c in w if c.isalpha())
            if len(letters) >= 4:
                assert letters in t
                break

    # before the fix this raised ValueError from the shrinker instead
    with pytest.raises(AssertionError):
        test()
