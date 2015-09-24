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

import sys
import unicodedata

import hypothesis.internal.distributions as dist
from hypothesis.internal.compat import hrange, hunichr, text_type, \
    binary_type
from hypothesis.searchstrategy.strategies import check_length, \
    SearchStrategy, check_data_type, MappedSearchStrategy

_spaces = [
    i for i in [
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
        20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 127, 128, 129, 130,
        131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144,
        145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158,
        159, 160, 5760, 8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200,
        8201, 8202, 8239, 8287, 12288] if i <= sys.maxunicode]


class OneCharStringStrategy(SearchStrategy):

    """A strategy which generates single character strings of text type."""
    specifier = text_type
    ascii_characters = u''.join(
        chr(i) for i in hrange(128)
    )
    zero_point = ord(u'0')

    def draw_parameter(self, random):
        alphabet_size = 1 + dist.geometric(random, 0.1)
        alphabet = []
        buckets = 10
        ascii_chance = random.randint(1, buckets)
        if ascii_chance < buckets:
            space_chance = random.randint(1, buckets - ascii_chance)
        else:
            space_chance = 0
        while len(alphabet) < alphabet_size:
            choice = random.randint(1, buckets)
            if choice <= ascii_chance:
                codepoint = dist.geometric(random, 1.0 / 127)
            elif choice <= ascii_chance + space_chance:
                while True:
                    i = dist.geometric(random, 2 / len(_spaces))
                    if i < len(_spaces):
                        codepoint = _spaces[i]
                        break
            else:
                codepoint = random.randint(0, sys.maxunicode)

            char = hunichr(codepoint)
            if self.is_good(char):
                alphabet.append(char)
        if u'\n' not in alphabet and not random.randint(0, 10):
            alphabet.append(u'\n')
        return tuple(alphabet)

    def is_good(self, char):
        return unicodedata.category(char) != u'Cs'

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
        if template < u'0':
            for i in hrange(ord(template) + 1, self.zero_point + 1):
                yield hunichr(i)

        for i in self.ascii_characters:
            if i < u'0':
                continue
            if i >= template:
                break
            yield i

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
