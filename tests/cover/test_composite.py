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

import pytest

import hypothesis.strategies as st
from hypothesis import find, given, assume
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import hrange


@st.composite
def badly_draw_lists(draw, m=0):
    length = draw(st.integers(m, m + 10))
    return [
        draw(st.integers()) for _ in hrange(length)
    ]


def test_simplify_draws():
    assert find(badly_draw_lists(), lambda x: len(x) >= 3) == [0] * 3


def test_can_pass_through_arguments():
    assert find(badly_draw_lists(5), lambda x: True) == [0] * 5
    assert find(badly_draw_lists(m=6), lambda x: True) == [0] * 6


@st.composite
def draw_ordered_with_assume(draw):
    x = draw(st.floats())
    y = draw(st.floats())
    assume(x < y)
    return (x, y)


@given(draw_ordered_with_assume())
def test_can_assume_in_draw(xy):
    assert xy[0] < xy[1]


def test_uses_definitions_for_reprs():
    assert repr(badly_draw_lists()) == 'badly_draw_lists()'
    assert repr(badly_draw_lists(1)) == 'badly_draw_lists(m=1)'
    assert repr(badly_draw_lists(m=1)) == 'badly_draw_lists(m=1)'


def test_errors_given_default_for_draw():
    with pytest.raises(InvalidArgument):
        @st.composite
        def foo(x=None):
            pass


def test_errors_given_function_of_no_arguments():
    with pytest.raises(InvalidArgument):
        @st.composite
        def foo():
            pass


def test_errors_given_kwargs_only():
    with pytest.raises(InvalidArgument):
        @st.composite
        def foo(**kwargs):
            pass


def test_can_use_pure_args():
    @st.composite
    def stuff(*args):
        return args[0](st.sampled_from(args[1:]))
    assert find(stuff(1, 2, 3, 4, 5), lambda x: True) == 1


def test_composite_of_lists():
    @st.composite
    def f(draw):
        return draw(st.integers()) + draw(st.integers())

    assert find(st.lists(f()), lambda x: len(x) >= 10) == [0] * 10
