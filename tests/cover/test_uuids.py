# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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
from hypothesis import find, given


@given(st.lists(st.uuids()))
def test_are_unique(ls):
    assert len(set(ls)) == len(ls)


@given(st.lists(st.uuids()), st.randoms())
def test_retains_uniqueness_in_simplify(ls, rnd):
    ts = find(st.lists(st.uuids()), lambda x: len(x) >= 5, random=rnd)
    assert len(ts) == len(set(ts)) == 5
