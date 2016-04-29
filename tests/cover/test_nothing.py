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

from hypothesis import strategies as st
from hypothesis import find, given
from hypothesis.errors import NoExamples, InvalidArgument


def test_resampling():
    x = find(
        st.lists(st.integers()).flatmap(
            lambda x: st.lists(st.sampled_from(x))),
        lambda x: len(x) >= 10 and len(set(x)) == 1)
    assert x == [0] * 10


@given(st.lists(st.nothing()))
def test_list_of_nothing(xs):
    assert xs == []


@given(st.sets(st.nothing()))
def test_set_of_nothing(xs):
    assert xs == set()


def test_validates_min_size():
    with pytest.raises(InvalidArgument):
        st.lists(st.nothing(), min_size=1).validate()


def test_one_of_is_or_identity():
    x = st.integers()
    assert (x | st.nothing()) is x
    assert (st.nothing() | x) is x


def test_function_composition():
    assert st.nothing().map(lambda x: 'hi').is_empty
    assert st.nothing().filter(lambda x: True).is_empty
    assert st.nothing().flatmap(lambda x: st.integers()).is_empty


def test_tuples_detect_empty_elements():
    assert st.tuples(st.nothing()).is_empty


def test_fixed_dictionaries_detect_empty_values():
    assert st.fixed_dictionaries({'a': st.nothing()}).is_empty


def test_one_of_empty():
    assert st.one_of() is st.nothing()


def test_no_examples():
    with pytest.raises(NoExamples):
        st.nothing().example()
