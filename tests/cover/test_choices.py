# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import hypothesis.strategies as st
from hypothesis import find, given
from tests.common.utils import raises


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


def test_can_use_a_choice_function_after_find():
    c = find(st.choices(), lambda c: True)
    ls = [1, 2, 3]
    assert c(ls) in ls


def test_choice_raises_index_error_on_empty():
    c = find(st.choices(), lambda c: True)
    with raises(IndexError):
        c([])
