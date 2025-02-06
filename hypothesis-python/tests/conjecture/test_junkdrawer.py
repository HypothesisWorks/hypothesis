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
import inspect

import pytest

from hypothesis import example, given, strategies as st
from hypothesis.internal.conjecture.junkdrawer import (
    IntList,
    LazySequenceCopy,
    NotFound,
    SelfOrganisingList,
    binary_search,
    endswith,
    replace_all,
    stack_depth_of_caller,
    startswith,
)
from hypothesis.internal.floats import clamp, float_to_int, sign_aware_lte


def test_out_of_range():
    x = LazySequenceCopy([1, 2, 3])

    with pytest.raises(IndexError):
        x[3]

    with pytest.raises(IndexError):
        x[-4]


def test_pass_through():
    x = LazySequenceCopy([1, 2, 3])
    assert x[0] == 1
    assert x[1] == 2
    assert x[2] == 3


def test_can_assign_without_changing_underlying():
    underlying = [1, 2, 3]
    x = LazySequenceCopy(underlying)
    x[1] = 10
    assert x[1] == 10
    assert underlying[1] == 2


def test_pop():
    x = LazySequenceCopy([2, 3])
    assert x.pop() == 3
    assert x.pop() == 2

    with pytest.raises(IndexError):
        x.pop()


@st.composite
def clamp_inputs(draw):
    lower = draw(st.floats(allow_nan=False))
    value = draw(st.floats(allow_nan=False))
    upper = draw(st.floats(min_value=lower, allow_nan=False))
    return (lower, value, upper)


@example((1, 5, 10))
@example((1, 10, 5))
@example((5, 10, 5))
@example((5, 1, 10))
@example((-5, 0.0, -0.0))
@example((0.0, -0.0, 5))
@example((-0.0, 0.0, 0.0))
@example((-0.0, -0.0, 0.0))
@given(clamp_inputs())
def test_clamp(input):
    lower, value, upper = input
    clamped = clamp(lower, value, upper)

    assert sign_aware_lte(lower, clamped)
    assert sign_aware_lte(clamped, upper)
    if sign_aware_lte(lower, value) and sign_aware_lte(value, upper):
        assert float_to_int(value) == float_to_int(clamped)
    if lower > value:
        assert float_to_int(clamped) == float_to_int(lower)
    if value > upper:
        assert float_to_int(clamped) == float_to_int(upper)


# this would be more robust as a stateful test, where each rule is a list operation
# on (1) the canonical python list and (2) its LazySequenceCopy. We would assert
# that the return values and lists match after each rule, and the original list
# is unmodified.
@pytest.mark.parametrize("should_mask", [True, False])
@given(lst=st.lists(st.integers(), min_size=1), data=st.data())
def test_pop_sequence_copy(lst, data, should_mask):
    original = copy.copy(lst)
    pop_i = data.draw(st.integers(0, len(lst) - 1))
    if should_mask:
        mask_i = data.draw(st.integers(0, len(lst) - 1))
        mask_value = data.draw(st.integers())

    def pop(l):
        if should_mask:
            l[mask_i] = mask_value
        return l.pop(pop_i)

    expected = copy.copy(lst)
    l = LazySequenceCopy(lst)

    assert pop(expected) == pop(l)
    assert list(l) == expected
    # modifications to the LazySequenceCopy should not modify the original list
    assert original == lst


def test_assignment():
    y = [1, 2, 3]
    x = LazySequenceCopy(y)
    x[-1] = 5
    assert list(x) == [1, 2, 5]
    x[-1] = 7
    assert list(x) == [1, 2, 7]


def test_replacement():
    result = replace_all([1, 1, 1, 1], [(1, 3, [3, 4])])
    assert result == [1, 3, 4, 1]


def test_int_list_cannot_contain_negative():
    with pytest.raises(ValueError):
        IntList([-1])


def test_int_list_can_contain_arbitrary_size():
    n = 2**65
    assert list(IntList([n])) == [n]


def test_int_list_of_length():
    assert list(IntList.of_length(10)) == [0] * 10


def test_int_list_equality():
    ls = [1, 2, 3]
    x = IntList(ls)
    y = IntList(ls)

    assert ls != x
    assert x != ls
    assert not (x == ls)  # noqa
    assert x == x
    assert x == y


def test_int_list_extend():
    x = IntList.of_length(3)
    n = 2**64 - 1
    x.extend([n])
    assert list(x) == [0, 0, 0, n]


def test_int_list_slice():
    x = IntList([1, 2])
    assert list(x[:1]) == [1]
    assert list(x[0:2]) == [1, 2]
    assert list(x[1:]) == [2]


def test_int_list_del():
    x = IntList([1, 2])
    del x[0]
    assert x == IntList([2])


@pytest.mark.parametrize("n", [0, 1, 30, 70])
def test_binary_search(n):
    i = binary_search(0, 100, lambda i: i <= n)
    assert i == n


def recur(i):
    assert len(inspect.stack(0)) == stack_depth_of_caller()
    if i >= 1:
        recur(i - 1)


def test_stack_size_detection():
    recur(100)


def test_self_organising_list_raises_not_found_when_none_satisfy():
    with pytest.raises(NotFound):
        SelfOrganisingList(range(20)).find(lambda x: False)


def test_self_organising_list_moves_to_front():
    count = 0

    def zero(n):
        nonlocal count
        count += 1
        return n == 0

    x = SelfOrganisingList(range(20))

    assert x.find(zero) == 0
    assert count == 20

    assert x.find(zero) == 0
    assert count == 21


@given(st.binary(), st.binary())
def test_startswith(b1, b2):
    assert b1.startswith(b2) == startswith(b1, b2)


@given(st.binary(), st.binary())
def test_endswith(b1, b2):
    assert b1.endswith(b2) == endswith(b1, b2)
