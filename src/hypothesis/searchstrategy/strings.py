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

from __future__ import division, print_function, absolute_import

import sys
import unicodedata

import hypothesis.internal.distributions as dist
from hypothesis.errors import InvalidArgument
from hypothesis.internal import charstree
from hypothesis.internal.compat import hunichr, text_type, binary_type
from hypothesis.searchstrategy.strategies import check_length, \
    SearchStrategy, check_data_type, MappedSearchStrategy


class OneCharStringStrategy(SearchStrategy):

    """A strategy which generates single character strings of text type."""
    specifier = text_type
    zero_point = ord(u'0')

    def __init__(self,
                 whitelist_categories=None,
                 blacklist_categories=None,
                 blacklist_characters=None,
                 min_codepoint=None,
                 max_codepoint=None):
        whitelist_categories = set(whitelist_categories or [])
        blacklist_categories = set(blacklist_categories or [])
        blacklist_characters = set(blacklist_characters or [])

        min_codepoint = int(min_codepoint or 0)
        max_codepoint = int(max_codepoint or sys.maxunicode)

        self.ascii_tree = charstree.filter_tree(
            charstree.ascii_tree(),
            whitelist_categories,
            blacklist_categories,
            blacklist_characters,
            min_codepoint,
            max_codepoint,
        )
        self.unicode_tree = charstree.filter_tree(
            charstree.unicode_tree(),
            whitelist_categories,
            blacklist_categories,
            blacklist_characters,
            min_codepoint,
            max_codepoint,
        )
        self.spaces_tree = charstree.filter_tree(
            self.unicode_tree,
            whitelist_categories=set(['Zs', 'Cc']),
            blacklist_characters=blacklist_characters,
            min_codepoint=min_codepoint,
            max_codepoint=max_codepoint,
        )
        self.blacklist_characters = blacklist_characters
        self.min_codepoint = min_codepoint
        self.max_codepoint = max_codepoint
        if not self.unicode_tree:
            raise InvalidArgument('No characters could be produced.'
                                  ' Try to reduce white/black categories list'
                                  ' or min/max allowed code points.')

    def draw_parameter(self, random):
        ascii_categories = charstree.categories(self.ascii_tree)
        unicode_categories = charstree.categories(self.unicode_tree)
        spaces_categories = charstree.categories(self.spaces_tree)

        alphabet_size = 1 + dist.geometric(random, 0.1)
        alphabet = []
        buckets = 10
        ascii_chance = random.randint(1, buckets)

        if spaces_categories and ascii_chance < buckets:
            space_chance = random.randint(1, buckets - ascii_chance)
        else:
            space_chance = 0

        while len(alphabet) < alphabet_size:
            choice = random.randint(1, buckets)

            if ascii_categories and choice <= ascii_chance:
                category = random.choice(ascii_categories)
                tree = self.ascii_tree
            elif spaces_categories and choice <= ascii_chance + space_chance:
                category = random.choice(spaces_categories)
                tree = self.spaces_tree
            else:
                category = random.choice(unicode_categories)
                tree = self.unicode_tree

            codepoint = charstree.random_codepoint(tree, category, random)
            alphabet.append(hunichr(codepoint))

        if u'\n' not in alphabet and not random.randint(0, 6):
            if self.is_good(u'\n'):
                alphabet.append(u'\n')

        return tuple(alphabet)

    def is_good(self, char):
        if char in self.blacklist_characters:
            return False

        categories = charstree.categories(self.unicode_tree)
        if unicodedata.category(char) not in categories:
            return False

        codepoint = ord(char)
        return self.min_codepoint <= codepoint <= self.max_codepoint

    def draw_template(self, random, p):
        return random.choice(p)

    def reify(self, value):
        return value

    def simplifiers(self, random, template):
        yield self.try_ascii
        i = self.zero_point
        while i < ord(template):
            yield self.try_shrink(i, 2 * i)
            i *= 2

    def try_shrink(self, lo, hi):
        def accept(random, template):
            x = ord(template)
            if x <= lo:
                return

            lb = lo
            while True:
                c = hunichr(lb)
                if self.is_good(c):
                    yield c
                new_lb = (lb + x) // 2
                if new_lb <= lb or new_lb >= hi:
                    return
                if new_lb > lb + 2:
                    c = hunichr(random.randint(lb + 1, new_lb - 1))
                    if self.is_good(c):
                        yield c
                lb = new_lb
        accept.__name__ = str(
            u'try_shrink(%d, %d)' % (lo, hi)
        )
        return accept

    def try_ascii(self, random, template):
        tree = self.ascii_tree

        if not tree:
            return

        zero_point = self.zero_point
        template = ord(template)

        if template < zero_point:
            min_codepoint, max_codepoint = template, zero_point
        elif template > zero_point:
            min_codepoint, max_codepoint = zero_point, template
        else:
            return

        subtree = charstree.filter_tree(
            tree, min_codepoint=min_codepoint, max_codepoint=max_codepoint)

        for codepoint in charstree.codepoints(subtree):
            yield hunichr(codepoint)

    def to_basic(self, template):
        return template

    def from_basic(self, data):
        check_data_type(text_type, data)
        check_length(1, data)
        return data


class StringStrategy(MappedSearchStrategy):

    """A strategy for text strings, defined in terms of a strategy for lists of
    single character text strings."""

    def __init__(self, list_of_one_char_strings_strategy):
        super(StringStrategy, self).__init__(
            strategy=list_of_one_char_strings_strategy
        )

    def __repr__(self):
        return u'StringStrategy()'

    def pack(self, ls):
        return u''.join(ls)


class BinaryStringStrategy(MappedSearchStrategy):

    """A strategy for strings of bytes, defined in terms of a strategy for
    lists of bytes."""

    def __repr__(self):
        return u'BinaryStringStrategy()'

    def pack(self, x):
        assert isinstance(x, list), repr(x)
        ba = bytearray(x)
        return binary_type(ba)
