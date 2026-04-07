# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""This example demonstrates testing a run length encoding scheme. That is, we
take a sequence and represent it by a shorter sequence where each 'run' of
consecutive equal elements is represented as a single element plus a count. So
e.g.

[1, 1, 1, 1, 2, 1] is represented as [[1, 4], [2, 1], [1, 1]]

This demonstrates the useful decode(encode(x)) == x invariant that is often
a fruitful source of testing with Hypothesis.

It also has an example of testing invariants in response to changes in the
underlying data.
"""

from hypothesis import assume, given, strategies as st


def run_length_encode(seq):
    """Encode a sequence as a new run-length encoded sequence."""
    if not seq:
        return []
    # By starting off the count at zero we simplify the iteration logic
    # slightly.
    result = [[seq[0], 0]]
    for s in seq:
        if (
            # If you uncomment this line this branch will be skipped and we'll
            # always append a new run of length 1. Note which tests fail.
            # False and
            s
            == result[-1][0]
            # Try uncommenting this line and see what problems occur:
            # and result[-1][-1] < 2
        ):
            result[-1][1] += 1
        else:
            result.append([s, 1])
    return result


def run_length_decode(seq):
    """Take a previously encoded sequence and reconstruct the original from
    it."""
    result = []
    for s, i in seq:
        for _ in range(i):
            result.append(s)
    return result


# We use lists of a type that should have a relatively high duplication rate,
# otherwise we'd almost never get any runs.
Lists = st.lists(st.integers(0, 10))


@given(Lists)
def test_decodes_to_starting_sequence(ls):
    """If we encode a sequence and then decode the result, we should get the
    original sequence back.

    Otherwise we've done something very wrong.
    """
    assert run_length_decode(run_length_encode(ls)) == ls


@given(Lists, st.data())
def test_duplicating_an_element_does_not_increase_length(ls, data):
    """The previous test could be passed by simply returning the input sequence
    so we need something that tests the compression property of our encoding.

    In this test we deliberately introduce or extend a run and assert
    that this does not increase the length of our encoding, because they
    should be part of the same run in the final result.
    """
    # We use assume to get a valid index into the list. We could also have used
    # e.g. flatmap, but this is relatively straightforward and will tend to
    # perform better.
    assume(ls)
    i = data.draw(st.integers(0, len(ls) - 1))
    ls2 = list(ls)
    # duplicating the value at i right next to it guarantees they are part of
    # the same run in the resulting compression.
    ls2.insert(i, ls2[i])
    assert len(run_length_encode(ls2)) == len(run_length_encode(ls))
