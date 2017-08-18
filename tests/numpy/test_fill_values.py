# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import hypothesis.strategies as st
from hypothesis import given
from tests.common.debug import minimal, find_any
from hypothesis.extra.numpy import FillValue, arrays


@given(arrays(object, 100, st.lists(max_size=0)))
def test_generated_lists_are_distinct(ls):
    assert len({id(x) for x in ls}) == len(ls)


@st.composite
def distinct_integers(draw):
    used = draw(st.shared(st.builds(set), key='distinct_integers.used'))
    i = draw(st.integers(0, 2 ** 64 - 1).filter(lambda x: x not in used))
    used.add(i)
    return i


@given(arrays('uint64', 10, distinct_integers()))
def test_does_not_reuse_distinct_integers(arr):
    assert len(set(arr)) == len(arr)


def test_may_reuse_distinct_integers_if_asked():
    find_any(
        arrays('uint64', 10, distinct_integers(), fill_value=FillValue.draw),
        lambda x: len(set(x)) < len(x)
    )


def test_minimizes_to_fill():
    result = minimal(arrays(float, 10, fill_value=3.0))
    assert (result == 3.0).all()
