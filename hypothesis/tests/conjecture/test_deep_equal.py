# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import copy
import math

import pytest

from hypothesis import given, strategies as st
from hypothesis.internal.conjecture.junkdrawer import deep_equal


def values(*, eq_divergent: bool = True):
    # If eq_divergent, include the leaf types where deep_equal intentionally
    # diverges from ==: floats (NaN, signed zero) and bools (True == 1).
    leaves = st.none() | st.integers() | st.text() | st.binary()
    if eq_divergent:
        leaves |= st.booleans() | st.floats()
    hashable = st.recursive(leaves, lambda v: st.tuples(v) | st.frozensets(v))
    return st.recursive(
        leaves,
        lambda v: (
            st.lists(v)
            | st.tuples(v)
            | st.dictionaries(hashable, v)
            | st.frozensets(hashable)
        ),
    )


@given(values())
def test_deep_equal_reflexive(v):
    # deepcopy so we can't trivially pass via an `is` shortcut
    assert deep_equal(v, copy.deepcopy(v))


@given(values(), values())
def test_deep_equal_symmetric(a, b):
    assert deep_equal(a, b) == deep_equal(b, a)


@given(values(eq_divergent=False), values(eq_divergent=False))
def test_deep_equal_matches_eq_without_floats(a, b):
    assert deep_equal(a, b) == (a == b)


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (math.nan, math.nan, True),
        (0.0, -0.0, False),
        (True, 1, False),
        (1, 1.0, False),
        ([math.nan], [math.nan], True),
        ({"a": math.nan}, {"a": math.nan}, True),
        ({0.0: 1}, {-0.0: 1}, False),
        ({math.nan}, {math.nan}, True),
        ({1, 2}, {1, 3}, False),
        ({"a": 1}, {"a": 2}, False),
        ({"a": 1}, {"a": 1, "b": 2}, False),
        ({1}, {1, 2}, False),
    ],
)
def test_deep_equal_explicit(a, b, expected):
    assert deep_equal(a, b) is expected
