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

import unicodedata

import pytest

from hypothesis import find
from hypothesis.errors import NoExamples, InvalidArgument
from hypothesis.strategies import characters


def test_bad_category_arguments():
    with pytest.raises(InvalidArgument):
        characters(
            whitelist_categories=['foo'], blacklist_categories=['bar']
        ).example()


def test_bad_codepoint_arguments():
    with pytest.raises(InvalidArgument):
        characters(min_codepoint=42, max_codepoint=24).example()


def test_exclude_all_available_range():
    with pytest.raises(InvalidArgument):
        characters(min_codepoint=ord('0'), max_codepoint=ord('0'),
                   blacklist_characters='0').example()


def test_when_nothing_could_be_produced():
    with pytest.raises(InvalidArgument):
        characters(whitelist_categories=['Cc'],
                   min_codepoint=ord('0'), max_codepoint=ord('9')).example()


def test_characters_of_specific_groups():
    st = characters(whitelist_categories=('Lu', 'Nd'))

    st.filter(lambda c: unicodedata.category(c) == 'Lu').example()
    st.filter(lambda c: unicodedata.category(c) == 'Nd').example()

    with pytest.raises(NoExamples):
        st.filter(lambda c: unicodedata.category(c) not in ('Lu', 'Nd')
                  ).example()


def test_exclude_characters_of_specific_groups():
    st = characters(blacklist_categories=('Lu', 'Nd'))

    st.filter(lambda c: unicodedata.category(c) != 'Lu').example()
    st.filter(lambda c: unicodedata.category(c) != 'Nd').example()

    with pytest.raises(NoExamples):
        st.filter(lambda c: unicodedata.category(c) in ('Lu', 'Nd')).example()


def test_find_one():
    char = find(characters(min_codepoint=48, max_codepoint=48), lambda _: True)
    assert char == u'0'


def test_find_something_rare():
    st = characters(whitelist_categories=['Zs'], min_codepoint=12288)

    st.filter(lambda c: unicodedata.category(c) == 'Zs').example()

    with pytest.raises(NoExamples):
        st.filter(lambda c: unicodedata.category(c) != 'Zs').example()


def test_blacklisted_characters():
    bad_chars = u'te02тест49st'
    st = characters(min_codepoint=ord('0'), max_codepoint=ord('9'),
                    blacklist_characters=bad_chars)

    assert '1' == find(st, lambda c: True)

    with pytest.raises(NoExamples):
        st.filter(lambda c: c in bad_chars).example()
