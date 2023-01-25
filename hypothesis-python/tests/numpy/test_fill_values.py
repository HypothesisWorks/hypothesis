# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given, strategies as st
from hypothesis.extra.numpy import arrays

from tests.common.debug import find_any, minimal


@given(arrays(object, 100, elements=st.builds(list)))
def test_generated_lists_are_distinct(ls):
    assert len(set(map(id, ls))) == len(ls)


@st.composite
def distinct_integers(draw):
    used = draw(st.shared(st.builds(set), key="distinct_integers.used"))
    i = draw(st.integers(0, 2**64 - 1).filter(lambda x: x not in used))
    used.add(i)
    return i


@given(arrays("uint64", 10, elements=distinct_integers()))
def test_does_not_reuse_distinct_integers(arr):
    assert len(set(arr)) == len(arr)


def test_may_reuse_distinct_integers_if_asked():
    find_any(
        arrays("uint64", 10, elements=distinct_integers(), fill=distinct_integers()),
        lambda x: len(set(x)) < len(x),
    )


def test_minimizes_to_fill():
    result = minimal(arrays(float, 10, fill=st.just(3.0)))
    assert (result == 3.0).all()


@given(
    arrays(
        dtype=float,
        elements=st.floats(allow_nan=False).filter(bool),
        shape=(3, 3, 3),
        fill=st.just(1.0),
    )
)
def test_fills_everything(x):
    assert x.all()
