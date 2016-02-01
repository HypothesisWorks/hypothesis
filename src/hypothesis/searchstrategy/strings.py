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

from hypothesis.errors import InvalidArgument
from hypothesis.control import assume
from hypothesis.internal.compat import hrange, hunichr, text_type, \
    binary_type
from hypothesis.searchstrategy.fixed import FixedStrategy
from hypothesis.searchstrategy.strategies import MappedSearchStrategy

CHR_ORDER = [
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'A', 'a', 'B', 'b', 'C', 'c', 'D', 'd', 'E', 'e', 'F', 'f', 'G', 'g',
    'H', 'h', 'I', 'i', 'J', 'j', 'K', 'k', 'L', 'l', 'M', 'm', 'N', 'n',
    'O', 'o', 'P', 'p', 'Q', 'q', 'R', 'r', 'S', 's', 'T', 't', 'U', 'u',
    'V', 'v', 'W', 'w', 'X', 'x', 'Y', 'y', 'Z', 'z',
    ' ',
    '_', '-', '=', '~',
    '"', "'",
    ':', ';', ',', '.', '?', '!',
    '(', ')', '{', '}', '[', ']', '<', '>',
    '*', '+', '/', '&', '|', '%',
    '#', '$', '@', '\\', '^', '`',
    '\t', '\n', '\r',
    '\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08',
    '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12', '\x13', '\x14',
    '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a', '\x1b', '\x1c', '\x1d',
    '\x1e', '\x1f',
]

REVERSE_CHR_ORDER = [0] * len(CHR_ORDER)
for i, c in enumerate(CHR_ORDER):
    REVERSE_CHR_ORDER[ord(c)] = i
assert sorted(REVERSE_CHR_ORDER) == list(range(127))


unicode_categories = set([
    'Cc', 'Cf', 'Cn', 'Co', 'Cs', 'Ll', 'Lm', 'Lo', 'Lt', 'Lu', 'Mc', 'Me',
    'Mn', 'Nd', 'Nl', 'No', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc',
    'Sk', 'Sm', 'So', 'Zl', 'Zp', 'Zs'
])


def int_to_chr(i):
    if i < 127:
        return CHR_ORDER[i]
    return hunichr(i)


def chr_to_int(c):
    i = ord(c)
    if i < 127:
        return REVERSE_CHR_ORDER[i]
    return i


class OneCharStringStrategy(FixedStrategy):

    """A strategy which generates single character strings of text type."""
    specifier = text_type
    zero_point = ord('0')

    def __init__(self,
                 whitelist_categories=None,
                 blacklist_categories=None,
                 blacklist_characters=None,
                 min_codepoint=None,
                 max_codepoint=None):
        FixedStrategy.__init__(self, 3)
        if whitelist_categories is not None:
            whitelist_categories = set(whitelist_categories)
        else:
            whitelist_categories = set(unicode_categories)
        self.whitelist_categories = whitelist_categories
        if blacklist_categories:
            self.whitelist_categories -= set(blacklist_categories)

        self.min_codepoint = int(min_codepoint or 0)
        self.max_codepoint = int(max_codepoint or sys.maxunicode)
        self.blacklist_characters = set(blacklist_characters or ())
        self.count = 0

        intervals_by_category = {}
        for i in hrange(0, max(128, self.max_codepoint + 1)):
            c = int_to_chr(i)
            if ord(c) < self.min_codepoint or ord(c) > self.max_codepoint:
                continue
            if c in self.blacklist_characters:
                continue
            cat = unicodedata.category(c)
            if cat not in self.whitelist_categories:
                continue
            self.count += 1
            intervals = intervals_by_category.setdefault(cat, [])
            if not intervals or i > intervals[-1][-1] + 1:
                intervals.append([i, i])
            else:
                assert i == intervals[-1][-1] + 1
                intervals[-1][-1] += 1

        self.intervals_by_category = sorted(intervals_by_category.values())
        self.allow_newlines = self.is_acceptable(u'\n')

        if not intervals_by_category:
            raise InvalidArgument('Empty set of allowed characters')

    def from_bytes(self, b):
        i = int.from_bytes(b, 'big')
        assume(i <= sys.maxunicode)
        return int_to_chr(i)

    def to_bytes(self, c):
        i = chr_to_int(c)
        return i.to_bytes(3, 'big')

    def is_acceptable(self, char):
        i = ord(char)
        if i < self.min_codepoint:
            return False
        if i > self.max_codepoint:
            return False
        if char in self.blacklist_characters:
            return False
        if unicodedata.category(char) not in self.whitelist_categories:
            return False
        return True

    def draw_value(self, random):
        if self.allow_newlines and random.randint(1, 10) == 10:
            return u'\n'
        cat = random.choice(self.intervals_by_category)
        interval = random.choice(cat)
        i = random.randint(*interval)
        return int_to_chr(i)


class StringStrategy(MappedSearchStrategy):

    """A strategy for text strings, defined in terms of a strategy for lists of
    single character text strings."""

    def __init__(self, list_of_one_char_strings_strategy):
        super(StringStrategy, self).__init__(
            strategy=list_of_one_char_strings_strategy
        )

    def __repr__(self):
        return 'StringStrategy()'

    def pack(self, ls):
        return u''.join(ls)


class BinaryStringStrategy(MappedSearchStrategy):

    """A strategy for strings of bytes, defined in terms of a strategy for
    lists of bytes."""

    def __repr__(self):
        return 'BinaryStringStrategy()'

    def pack(self, x):
        assert isinstance(x, list), repr(x)
        ba = bytearray(x)
        return binary_type(ba)
