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
from hypothesis.errors import InvalidArgument


def test_no_args():
    assert st.text() is st.text()


def test_tuple_lengths():
    assert st.tuples(st.integers()) is st.tuples(st.integers())
    assert st.tuples(st.integers()) is not st.tuples(
        st.integers(), st.integers())


def test_values():
    assert st.integers() is not st.integers(min_value=1)


def test_alphabet_key():
    assert st.text(alphabet='abcs') is st.text(alphabet='abcs')


def test_does_not_error_on_unhashable_posarg():
    st.text(['a', 'b', 'c'])


def test_does_not_error_on_unhashable_kwarg():
    with pytest.raises(InvalidArgument):
        st.builds(lambda alphabet: 1, alphabet=['a', 'b', 'c']).validate()


def test_caches_floats_sensitively():
    assert st.floats(min_value=0.0) is st.floats(min_value=0.0)
    assert st.floats(min_value=0.0) is not st.floats(min_value=0)
    assert st.floats(min_value=0.0) is not st.floats(min_value=-0.0)
