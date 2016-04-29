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
from hypothesis import find, given
from hypothesis.errors import InvalidArgument


def test_exhaustion():
    @given(st.lists(st.text(), min_size=10), st.choices())
    def test(ls, choice):
        while ls:
            l = choice(ls)
            assert l in ls
            ls.remove(l)
    test()


@given(st.choices(), st.choices())
def test_choice_is_shared(choice1, choice2):
    assert choice1 is choice2


def test_cannot_use_choices_within_find():
    with pytest.raises(InvalidArgument):
        find(st.choices(), lambda c: True)


def test_fails_to_draw_from_empty_sequence():
    @given(st.choices())
    def test(choice):
        choice([])

    with pytest.raises(IndexError):
        test()
