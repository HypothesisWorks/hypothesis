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

"""Tests for specific string representations of values."""


from __future__ import division, print_function, absolute_import

import sys
import unittest
from collections import namedtuple

import pytest

import hypothesis.specifiers as specifiers
from hypothesis.utils.show import show


def test_show_for_nasty_floats():
    assert show(float(u'inf')) == u"float('inf')"
    assert show(float(u'-inf')) == u"float('-inf')"
    assert show(float(u'nan')) == u"float('nan')"


def test_nice_strint_for_nice_floats():
    assert show(0.5) == repr(0.5)


def test_show_for_nice_complex():
    assert show(1 + 1j) == u'(1+1j)'


def test_show_for_nasty_complex():
    assert show(
        complex(float(u'inf'), 0.0)) == u"complex('inf+0j')"


@pytest.mark.skipif(
    sys.version_info < (2, 7), reason=u'complex is picky in python 2.6')
def test_show_for_nasty_in_just():
    assert show(
        specifiers.just(complex(u'inf+1.9j'))
    ) == u"Just(value=complex('inf+1.9j'))"


def test_show_for_sets_is_not_a_dict():
    assert show(set()) == repr(set())
    assert show(frozenset()) == repr(frozenset())


def test_non_empty_frozensets_should_use_set_representation():
    assert show(frozenset([int])) == u'frozenset({int})'


def test_just_show_should_respect_its_values_reprs():
    class Stuff(object):

        def __repr__(self):
            return u'Things()'
    assert show(
        specifiers.Just(Stuff())
    ) == u'Just(value=Things())'


def test_uses_show_inside_named_tuples():
    Foo = namedtuple(u'Foo', (u'b', u'a'))
    assert show(
        Foo(1, float(u'nan'))
    ) == u"Foo(b=1, a=float('nan'))"


def test_uses_show_inside_unnamed_tuples():
    assert show((1, float(u'nan'))) == u"(1, float('nan'))"


@pytest.mark.skipif(
    sys.version_info < (2, 7), reason=u'complex is picky in python 2.6')
def test_does_not_strip_brackets_when_not_present():
    assert show(complex(u'nanj')) == u"complex('nanj')"


class X(object):

    def __init__(self, x):
        self.x = x


def test_can_nicely_display_things_without_repr():
    assert show(X(1)) == u'X(x=1)'


def test_uses_binary_literals_for_binary_type():
    assert show(b'foo') == u"b'foo'"


def test_uses_text_literals_for_text_type():
    assert show(u'foo') == u"'foo'"


def test_no_trailing_L_on_ints():
    s = u'1000000000000000000000000000000000000000000000000000'
    i = int(s)
    assert show(i) == s


def test_show_of_a_function_is_its_name():
    def foo_bar_baz():
        pass

    assert show(foo_bar_baz) == u'foo_bar_baz'


def test_show_of_object_is_object():
    assert show(object()) == u'object()'


class SomeObject(object):
    pass


def test_show_of_object_is_class():
    assert show(SomeObject()) == u'SomeObject()'


def test_show_of_bool_is_repr():
    assert show(False) == u'False'
    assert show(True) == u'True'


def test_show_of_none_is_repr():
    assert show(None) == u'None'


def test_list_str_is_repr():
    assert show([1, 2, 3]) == u'[1, 2, 3]'


def test_set_str_is_sorted_repr():
    assert show(set((4, 3, 2, 1))) == u'{1, 2, 3, 4}'


def test_frozenset_str_is_sorted_repr():
    assert show(frozenset(set((4, 3, 2, 1)))) == u'frozenset({1, 2, 3, 4})'


def test_dict_str_is_sorted_repr():
    assert show({1: 2, 2: 3, 3: 4, 4: 5}) == u'{1: 2, 2: 3, 3: 4, 4: 5}'


def test_show_of_1_tuple_includes_trailing_comma():
    assert show((1,)) == u'(1,)'


class TestEvalSelfTC(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestEvalSelfTC, self).__init__(*args, **kwargs)

    def test_can_eval_self(self):
        eval(show(self))


class TestEvalSelf(object):

    def test_can_eval_self(self):
        eval(show(self))


def test_can_handle_recursion():
    x = []
    x.append(x)
    assert show(x) == u'[(...)]'

    d = {}
    d[1] = d
    assert show(d) == u'{1: (...)}'

    t = ([],)
    t[0].append(t)
    assert show(t) == u'([(...)],)'

    class Foo(object):
        pass

    f = Foo()
    f.stuff = f
    assert show(f) == u'Foo(stuff=(...))'
