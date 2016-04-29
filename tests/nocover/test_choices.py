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
from hypothesis import given, settings
from tests.common.utils import raises, capture_out
from hypothesis.database import ExampleDatabase
from hypothesis.internal.compat import hrange


def test_stability():
    @given(
        st.lists(st.text(min_size=1, max_size=1), unique=True, min_size=5),
        st.choices(),
    )
    @settings(
        database=ExampleDatabase(),
    )
    def test_choose_and_then_fail(ls, choice):
        for _ in hrange(100):
            choice(ls)
        assert False

    # Run once first for easier debugging
    with raises(AssertionError):
        test_choose_and_then_fail()

    with capture_out() as o:
        with raises(AssertionError):
            test_choose_and_then_fail()
    out1 = o.getvalue()
    with capture_out() as o:
        with raises(AssertionError):
            test_choose_and_then_fail()
    out2 = o.getvalue()
    assert out1 == out2
    assert 'Choice #100:' in out1
