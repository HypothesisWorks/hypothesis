# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""Tests for specific string representations of values."""

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import unittest
from collections import namedtuple

import hypothesis.descriptors as descriptors
from hypothesis.searchstrategy import nice_string


def test_nice_string_for_nasty_floats():
    assert nice_string(float('inf')) == "float('inf')"
    assert nice_string(float('-inf')) == "float('-inf')"
    assert nice_string(float('nan')) == "float('nan')"


def test_nice_strint_for_nice_floats():
    assert nice_string(0.5) == repr(0.5)


def test_nice_string_for_nice_complex():
    assert nice_string(1 + 1j) == '(1+1j)'


def test_nice_string_for_nasty_complex():
    assert nice_string(
        complex(float('inf'), 0.0)) == "complex('inf+0j')"


def test_nice_string_for_nasty_in_just():
    assert nice_string(
        descriptors.just(complex('inf+1.9j'))
    ) == "Just(value=complex('inf+1.9j'))"


def test_nice_string_for_sets_is_not_a_dict():
    assert nice_string(set()) == repr(set())
    assert nice_string(frozenset()) == repr(frozenset())


def test_non_empty_frozensets_should_use_set_representation():
    assert nice_string(frozenset([int])) == 'frozenset({int})'


def test_just_nice_string_should_respect_its_values_reprs():
    class Stuff(object):

        def __repr__(self):
            return 'Things()'
    assert nice_string(
        descriptors.Just(Stuff())
    ) == 'Just(value=Things())'


def test_uses_nice_string_inside_named_tuples():
    Foo = namedtuple('Foo', ('b', 'a'))
    assert nice_string(
        Foo(1, float('nan'))
    ) == "Foo(b=1, a=float('nan'))"


def test_uses_nice_string_inside_unnamed_tuples():
    assert nice_string((1, float('nan'))) == "(1, float('nan'))"


def test_does_not_strip_brackets_when_not_present():
    assert nice_string(complex('nanj')) == "complex('nanj')"


class X(object):

    def __init__(self, x):
        self.x = x


def test_can_nicely_display_things_without_repr():
    assert nice_string(X(1)) == 'X(x=1)'


def test_uses_binary_literals_for_binary_type():
    assert nice_string(b'foo') == "b'foo'"


def test_uses_text_literals_for_text_type():
    assert nice_string('foo') == "'foo'"


def test_no_trailing_L_on_ints():
    s = '1000000000000000000000000000000000000000000000000000'
    i = int(s)
    assert nice_string(i) == s


def test_nice_string_of_a_function_is_its_name():
    def foo_bar_baz():
        pass

    assert nice_string(foo_bar_baz) == 'foo_bar_baz'


def test_nice_string_of_object_is_object():
    assert nice_string(object()) == 'object()'


class SomeObject(object):
    pass


def test_nice_string_of_object_is_class():
    assert nice_string(SomeObject()) == 'SomeObject()'


def test_nice_string_of_bool_is_repr():
    assert nice_string(False) == 'False'
    assert nice_string(True) == 'True'


def test_nice_string_of_none_is_repr():
    assert nice_string(None) == 'None'


def test_list_str_is_repr():
    assert nice_string([1, 2, 3]) == '[1, 2, 3]'


def test_set_str_is_sorted_repr():
    assert nice_string({4, 3, 2, 1}) == '{1, 2, 3, 4}'


def test_frozenset_str_is_sorted_repr():
    assert nice_string(frozenset({4, 3, 2, 1})) == 'frozenset({1, 2, 3, 4})'


def test_dict_str_is_sorted_repr():
    assert nice_string({1: 2, 2: 3, 3: 4, 4: 5}) == '{1: 2, 2: 3, 3: 4, 4: 5}'


def test_nice_string_of_1_tuple_includes_trailing_comma():
    assert nice_string((1,)) == '(1,)'


class TestEvalSelfTC(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestEvalSelfTC, self).__init__(*args, **kwargs)

    def test_can_eval_self(self):
        eval(nice_string(self))


class TestEvalSelf(object):

    def test_can_eval_self(self):
        eval(nice_string(self))


def test_can_handle_recursion():
    x = []
    x.append(x)
    assert nice_string(x) == '[(...)]'

    d = {}
    d[1] = d
    assert nice_string(d) == "{1: (...)}"

    t = ([],)
    t[0].append(t)
    assert nice_string(t) == "([(...)],)"

    class Foo(object):
        pass

    f = Foo()
    f.stuff = f
    assert nice_string(f) == "Foo(stuff=(...))"
