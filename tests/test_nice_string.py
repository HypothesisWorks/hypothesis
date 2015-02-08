# coding=utf-8

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals, division

# END HEADER

"""Tests for specific string representations of values."""

from hypothesis.searchstrategy import nice_string
import hypothesis.descriptors as descriptors
from collections import namedtuple


def test_nice_string_for_nasty_floats():
    assert nice_string(float('inf')) == "float('inf')"
    assert nice_string(float('-inf')) == "float('-inf')"
    assert nice_string(float('nan')) == "float('nan')"


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
