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

from hypothesis import strategies as st
from hypothesis import find, note, given, settings


@given(st.streaming(st.integers(min_value=0)), st.random_module())
@settings(buffer_size=200, max_shrinks=5, max_examples=10)
def test_can_eval_stream_inside_find(stream, rnd):
    x = find(
        st.lists(st.integers(min_value=0), min_size=10),
        lambda t: any(t > s for (t, s) in zip(t, stream)),
        settings=settings(database=None, max_shrinks=2000, max_examples=2000)
    )
    note('x: %r' % (x,))
    note('Evalled: %r' % (stream,))
    assert len([1 for i, v in enumerate(x) if stream[i] < v]) == 1
