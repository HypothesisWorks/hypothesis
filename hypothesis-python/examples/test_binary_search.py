# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""This file demonstrates testing a binary search.

It's a useful example because the result of the binary search is so clearly
determined by the invariants it must satisfy, so we can simply test for those
invariants.

It also demonstrates the useful testing technique of testing how the answer
should change (or not) in response to movements in the underlying data.
"""

from hypothesis import given, strategies as st


def binary_search(ls, v):
    """Take a list ls and a value v such that ls is sorted and v is comparable
    with the elements of ls.

    Return an index i such that 0 <= i <= len(v) with the properties:

    1. ls.insert(i, v) is sorted
    2. ls.insert(j, v) is not sorted for j < i
    """
    # Without this check we will get an index error on the next line when the
    # list is empty.
    if not ls:
        return 0

    # Without this check we will miss the case where the insertion point should
    # be zero: The invariant we maintain in the next section is that lo is
    # always strictly lower than the insertion point.
    if v <= ls[0]:
        return 0

    # Invariant: There is no insertion point i with i <= lo
    lo = 0

    # Invariant: There is an insertion point i with i <= hi
    hi = len(ls)
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if v > ls[mid]:
            # Inserting v anywhere below mid would result in an unsorted list
            # because it's > the value at mid. Therefore mid is a valid new lo
            lo = mid
        # Uncommenting the following lines will cause this to return a valid
        # insertion point which is not always minimal.
        # elif v == ls[mid]:
        #   return mid
        else:
            # Either v == ls[mid] in which case mid is a valid insertion point
            # or v < ls[mid], in which case all valid insertion points must be
            # < hi. Either way, mid is a valid new hi.
            hi = mid
    assert lo + 1 == hi
    # We now know that there is a valid insertion point <= hi and there is no
    # valid insertion point < hi because hi - 1 is lo. Therefore hi is the
    # answer we were seeking
    return hi


def is_sorted(ls):
    """Is this list sorted?"""
    return all(x <= y for x, y in zip(ls, ls[1:]))


Values = st.integers()

# We generate arbitrary lists and turn this into generating sorting lists
# by just sorting them.
SortedLists = st.lists(Values).map(sorted)

# We could also do it this way, but that would be a bad idea:
# SortedLists = st.lists(Values).filter(is_sorted)
# The problem is that Hypothesis will only generate long sorted lists with very
# low probability, so we are much better off post-processing values into the
# form we want than filtering them out.


@given(ls=SortedLists, v=Values)
def test_insert_is_sorted(ls, v):
    """We test the first invariant: binary_search should return an index such
    that inserting the value provided at that index would result in a sorted
    set."""
    ls.insert(binary_search(ls, v), v)
    assert is_sorted(ls)


@given(ls=SortedLists, v=Values)
def test_is_minimal(ls, v):
    """We test the second invariant: binary_search should return an index such
    that no smaller index is a valid insertion point for v."""
    for i in range(binary_search(ls, v)):
        ls2 = list(ls)
        ls2.insert(i, v)
        assert not is_sorted(ls2)


@given(ls=SortedLists, v=Values)
def test_inserts_into_same_place_twice(ls, v):
    """In this we test a *consequence* of the second invariant: When we insert
    a value into a list twice, the insertion point should be the same both
    times. This is because we know that v is > the previous element and == the
    next element.

    In theory if the former passes, this should always pass. In practice,
    failures are detected by this test with much higher probability because it
    deliberately puts the data into a shape that is likely to trigger a
    failure.

    This is an instance of a good general category of test: Testing how the
    function moves in responses to changes in the underlying data.
    """
    i = binary_search(ls, v)
    ls.insert(i, v)
    assert binary_search(ls, v) == i
