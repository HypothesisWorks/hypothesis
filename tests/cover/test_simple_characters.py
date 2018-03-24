# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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
from hypothesis.errors import InvalidArgument
from tests.common.debug import find_any, assert_no_examples
from hypothesis.strategies import characters
from hypothesis.internal.compat import text_type


def test_nonexistent_category_argument():
    with pytest.raises(InvalidArgument):
        characters(blacklist_categories=['foo']).example()


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

    find(st, lambda c: unicodedata.category(c) == 'Lu')
    find(st, lambda c: unicodedata.category(c) == 'Nd')

    assert_no_examples(
        st, lambda c: unicodedata.category(c) not in ('Lu', 'Nd'))


def test_characters_of_major_categories():
    st = characters(whitelist_categories=('L', 'N'))
    find(st, lambda c: unicodedata.category(c).startswith('L'))
    find(st, lambda c: unicodedata.category(c).startswith('N'))
    assert_no_examples(
        st, lambda c: unicodedata.category(c)[0] not in ('L', 'N'))


def test_exclude_characters_of_specific_groups():
    st = characters(blacklist_categories=('Lu', 'Nd'))

    find(st, lambda c: unicodedata.category(c) != 'Lu')
    find(st, lambda c: unicodedata.category(c) != 'Nd')

    assert_no_examples(st, lambda c: unicodedata.category(c) in ('Lu', 'Nd'))


def test_exclude_characters_of_major_categories():
    st = characters(blacklist_categories=('L', 'N'))
    find(st, lambda c: not unicodedata.category(c).startswith('L'))
    find(st, lambda c: not unicodedata.category(c).startswith('N'))
    assert_no_examples(st, lambda c: unicodedata.category(c)[0] in ('L', 'N'))


def test_find_one():
    char = find(characters(min_codepoint=48, max_codepoint=48), lambda _: True)
    assert char == u'0'


def test_find_something_rare():
    st = characters(whitelist_categories=['Zs'], min_codepoint=12288)

    find(st, lambda c: unicodedata.category(c) == 'Zs')

    assert_no_examples(st, lambda c: unicodedata.category(c) != 'Zs')


def test_whitelisted_characters_alone():
    with pytest.raises(InvalidArgument):
        characters(whitelist_characters=u'te02тест49st').example()


def test_whitelisted_characters_overlap_blacklisted_characters():
    good_chars = u'te02тест49st'
    bad_chars = u'ts94тсет'
    with pytest.raises(InvalidArgument) as exc:
        characters(min_codepoint=ord('0'), max_codepoint=ord('9'),
                   whitelist_characters=good_chars,
                   blacklist_characters=bad_chars).example()
        assert repr(good_chars) in text_type(exc)
        assert repr(bad_chars) in text_type(exc)


def test_whitelisted_characters_override():
    good_characters = u'teтестst'
    st = characters(min_codepoint=ord('0'), max_codepoint=ord('9'),
                    whitelist_characters=good_characters)

    find_any(st, lambda c: c in good_characters)
    find_any(st, lambda c: c in '0123456789')

    assert_no_examples(st, lambda c: c not in good_characters + '0123456789')


def test_blacklisted_characters():
    bad_chars = u'te02тест49st'
    st = characters(min_codepoint=ord('0'), max_codepoint=ord('9'),
                    blacklist_characters=bad_chars)

    assert '1' == find(st, lambda c: True)

    assert_no_examples(st, lambda c: c in bad_chars)


def test_whitelist_characters_disjoint_blacklist_characters():
    good_chars = u'123abc'
    bad_chars = u'456def'
    st = characters(min_codepoint=ord('0'), max_codepoint=ord('9'),
                    blacklist_characters=bad_chars,
                    whitelist_characters=good_chars)

    assert_no_examples(st, lambda c: c in bad_chars)
