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

from hypothesis import assume, given, strategies as st
from hypothesis.internal.conjecture.junkdrawer import IntList

non_neg_lists = st.lists(st.integers(min_value=0, max_value=2**63 - 1))


@given(non_neg_lists)
def test_intlist_is_equal_to_itself(ls):
    assert IntList(ls) == IntList(ls)


@given(non_neg_lists, non_neg_lists)
def test_distinct_int_lists_are_not_equal(x, y):
    assume(x != y)
    assert IntList(x) != IntList(y)


def test_basic_equality():
    x = IntList([1, 2, 3])
    assert x == x
    t = x != x
    assert not t
    assert x != "foo"

    s = x == "foo"
    assert not s


def test_error_on_invalid_value():
    with pytest.raises(ValueError):
        IntList([-1])


def test_extend_by_too_large():
    x = IntList()
    ls = [1, 10**6]
    x.extend(ls)
    assert list(x) == ls
