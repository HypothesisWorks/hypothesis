# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import unicodedata
from random import Random

import pytest

from hypothesis import find, given, Settings
from hypothesis.strategies import text, binary, tuples


def test_can_minimize_up_to_zero():
    s = find(text(), lambda x: len([t for t in x if t <= u'0']) >= 10)
    assert s == u'0' * 10


def test_minimizes_towards_ascii_zero():
    s = find(text(), lambda x: any(t < u'0' for t in x))
    assert len(s) == 1
    assert ord(s) == ord(u'0') - 1


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


def test_can_safely_mix_simplifiers():
    from hypothesis.searchstrategy.strings import OneCharStringStrategy
    from hypothesis.internal.debug import some_template

    s = OneCharStringStrategy()
    r = Random(1)
    t1 = some_template(s, r)
    while True:
        t2 = some_template(s, r)
        if t1 != t2:
            break
    for u in (t1, t2):
        for v in (t1, t2):
            for simplify in s.simplifiers(r, u):
                for w in simplify(r, v):
                    assert not s.strictly_simpler(v, w)


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


@given(text(min_size=1, max_size=1), settings=Settings(max_examples=2000))
def test_does_not_generate_surrogates(t):
    assert unicodedata.category(t) != u'Cs'


def test_does_not_simplify_into_surrogates():
    f = find(text(), lambda x: x >= u'\udfff')
    assert f == u'\ue000'
    f = find(text(), lambda x: len([t for t in x if t >= u'\udfff']) >= 10)
    assert f == u'\ue000' * 10


@given(text(alphabet=[u'a', u'b']))
def test_respects_alphabet_if_list(xs):
    assert set(xs).issubset(set(u'ab'))


@given(text(alphabet=u'cdef'))
def test_respects_alphabet_if_string(xs):
    assert set(xs).issubset(set(u'cdef'))
