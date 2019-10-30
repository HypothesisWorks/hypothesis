# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import pytest

import hypothesis.strategies as st
from hypothesis import given
from hypothesis._settings import note_deprecation
from hypothesis.errors import HypothesisDeprecationWarning


def test_note_deprecation_blames_right_code_issue_652():
    msg = "this is an arbitrary deprecation warning message"

    @st.composite
    def deprecated_strategy(draw):
        draw(st.none())
        note_deprecation(msg, since="RELEASEDAY")

    @given(deprecated_strategy())
    def f(x):
        pass

    with pytest.warns(HypothesisDeprecationWarning) as log:
        f()

    assert len(log) == 1
    (record,) = log
    # We got the warning we expected, from the right file
    assert isinstance(record.message, HypothesisDeprecationWarning)
    assert record.message.args == (msg,)
    assert record.filename == __file__


@given(
    x=st.one_of(st.just(0) | st.just(1)),
    y=st.one_of(st.just(0) | st.just(1) | st.just(2)),
)
def test_performance_issue_2027(x, y):
    pass
