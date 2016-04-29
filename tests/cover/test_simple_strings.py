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

import unicodedata
from random import Random

import pytest

from hypothesis import find, given, settings
from hypothesis.strategies import text, binary, tuples, characters


def test_can_minimize_up_to_zero():
    s = find(text(), lambda x: any(lambda t: t <= u'0' for t in x))
    assert s == u'0'


def test_minimizes_towards_ascii_zero():
    s = find(text(), lambda x: any(t < u'0' for t in x))
    assert s == chr(ord(u'0') - 1)


def test_can_handle_large_codepoints():
    s = find(text(), lambda x: x >= u'☃')
    assert s == u'☃'


def test_can_find_mixed_ascii_and_non_ascii_strings():
    s = find(
        text(), lambda x: (
            any(t >= u'☃' for t in x) and
            any(ord(t) <= 127 for t in x)))
    assert len(s) == 2
    assert sorted(s) == [u'0', u'☃']


def test_will_find_ascii_examples_given_the_chance():
    s = find(
        tuples(text(max_size=1), text(max_size=1)),
        lambda x: x[0] and (x[0] < x[1]))
    assert ord(s[1]) == ord(s[0]) + 1
    assert u'0' in s


def test_finds_single_element_strings():
    assert find(text(), bool, random=Random(4)) == u'0'


def test_binary_respects_changes_in_size():
    @given(binary())
    def test_foo(x):
        assert len(x) <= 10
    with pytest.raises(AssertionError):
        test_foo()

    @given(binary(max_size=10))
    def test_foo(x):
        assert len(x) <= 10
    test_foo()


@given(text(min_size=1, max_size=1))
@settings(max_examples=2000)
def test_does_not_generate_surrogates(t):
    assert unicodedata.category(t) != u'Cs'


def test_does_not_simplify_into_surrogates():
    f = find(text(average_size=25.0), lambda x: x >= u'\udfff')
    assert f == u'\ue000'
    f = find(
        text(average_size=25.0),
        lambda x: len([t for t in x if t >= u'\udfff']) >= 10)
    assert f == u'\ue000' * 10


@given(text(alphabet=[u'a', u'b']))
def test_respects_alphabet_if_list(xs):
    assert set(xs).issubset(set(u'ab'))


@given(text(alphabet=u'cdef'))
def test_respects_alphabet_if_string(xs):
    assert set(xs).issubset(set(u'cdef'))


@given(text())
def test_can_encode_as_utf8(s):
    s.encode('utf-8')


@given(text(characters(blacklist_characters=u'\n')))
def test_can_blacklist_newlines(s):
    assert u'\n' not in s


@given(text(characters(blacklist_categories=('Cc', 'Cs'))))
def test_can_exclude_newlines_by_category(s):
    assert u'\n' not in s


@given(text(characters(max_codepoint=127)))
def test_can_restrict_to_ascii_only(s):
    s.encode('ascii')


def test_fixed_size_bytes_just_draw_bytes():
    from hypothesis.internal.conjecture.data import TestData
    x = TestData.for_buffer(b'foo')
    assert x.draw(binary(min_size=3, max_size=3)) == b'foo'
