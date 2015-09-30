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

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import sys
import random
import unicodedata

import pytest

from hypothesis.internal import charstree
from hypothesis.internal.compat import hunichr


def test_ascii_tree():
    tree = charstree.ascii_tree()
    assert isinstance(tree, dict)


def test_unicode_tree():
    tree = charstree.unicode_tree()
    assert isinstance(tree, dict)


def test_ascii_tree_categories():
    tree = charstree.ascii_tree()
    expected = list(set([unicodedata.category(hunichr(i))
                         for i in range(0, 128)]))
    actual = charstree.categories(tree)
    assert sorted(expected) == sorted(actual)


def test_unicode_tree_categories():
    tree = charstree.unicode_tree()
    expected = list(set([unicodedata.category(hunichr(i))
                         for i in range(0, sys.maxunicode + 1)]))
    actual = charstree.categories(tree)
    assert sorted(expected) == sorted(actual)


def test_ascii_tree_codepoints():
    tree = charstree.ascii_tree()
    expected = list(range(0, 128))
    actual = sorted(list(charstree.codepoints(tree)))
    assert expected == actual


def test_unicode_tree_codepoints():
    tree = charstree.unicode_tree()
    expected = list(range(0, sys.maxunicode + 1))
    actual = sorted(list(charstree.codepoints(tree)))
    assert expected == actual


def test_category_by_codepoint():
    tree = charstree.unicode_tree()
    assert 'Nd' == charstree.category_by_codepoint(tree, ord(u'1'))
    assert 'Ll' == charstree.category_by_codepoint(tree, ord(u'я'))

    tree = charstree.ascii_tree()
    assert charstree.category_by_codepoint(tree, ord(u'я')) is None


def test_filter_tree():
    tree = charstree.ascii_tree()
    new_tree = charstree.filter_tree(
        tree, min_codepoint=ord('0'), max_codepoint=ord('9'))
    expected = list(range(ord('0'), ord('9') + 1))
    actual = list(charstree.codepoints(new_tree))
    assert expected == actual


def test_assert_on_searching_random_codepoint_for_empty_tree():
    with pytest.raises(AssertionError):
        charstree.random_codepoint({}, '-', random)
