# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import sys
import base64
import unicodedata

import hypothesis.specifiers as specifiers
import hypothesis.internal.distributions as dist
from hypothesis.internal.compat import hrange, hunichr, text_type, \
    binary_type
from hypothesis.searchstrategy.strategies import BadData, SearchStrategy, \
    MappedSearchStrategy, strategy, check_type, check_length, \
    check_data_type


class OneCharStringStrategy(SearchStrategy):

    """A strategy which generates single character strings of text type."""
    specifier = text_type
    ascii_characters = ''.join(
        chr(i) for i in hrange(128)
    )
    zero_point = ord('0')

    def produce_parameter(self, random):
        alphabet_size = 1 + dist.geometric(random, 0.1)
        alphabet = []
        while len(alphabet) < alphabet_size:
            if random.randint(0, 10):
                codepoint = random.randint(0, sys.maxunicode)
            else:
                codepoint = dist.geometric(random, 1.0 / 127)

            char = hunichr(codepoint)
            if unicodedata.category(char) != 'Cs':
                alphabet.append(char)
        return tuple(alphabet)

    def produce_template(self, context, p):
        return context.random.choice(p)

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
                yield hunichr(lb)
                new_lb = (lb + x) // 2
                if new_lb <= lb or new_lb >= hi:
                    return
                if new_lb > lb + 2:
                    yield hunichr(random.randint(lb + 1, new_lb - 1))
                lb = new_lb
        accept.__name__ = str(
            'try_shrink(%d, %d)' % (lo, hi)
        )
        return accept

    def try_ascii(self, random, template):
        if template < '0':
            for i in hrange(ord(template) + 1, self.zero_point + 1):
                yield hunichr(i)

        for i in self.ascii_characters:
            if i < '0':
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
        return 'StringStrategy()'

    def pack(self, ls):
        return ''.join(ls)


class BinaryStringStrategy(MappedSearchStrategy):

    """A strategy for strings of bytes, defined in terms of a strategy for
    lists of bytes."""

    def __repr__(self):
        return 'BinaryStringStrategy()'

    def pack(self, x):
        assert isinstance(x, list), repr(x)
        ba = bytearray(x)
        return binary_type(ba)

    def to_basic(self, value):
        check_type(tuple, value)
        if value:
            check_type(int, value[0])
        packed = binary_type(bytearray(value))
        return base64.b64encode(packed).decode('utf-8')

    def from_basic(self, data):
        check_data_type(text_type, data)
        try:
            return tuple(bytearray(base64.b64decode(data.encode('utf-8'))))
        except Exception as e:
            raise BadData(*e.args)


@strategy.extend(specifiers.Strings)
def define_text_type_from_alphabet(specifier, settings):
    if not specifier.alphabet:
        return StringStrategy(strategy([], settings))
    return StringStrategy(strategy(
        [specifiers.sampled_from(specifier.alphabet)], settings))


@strategy.extend_static(text_type)
def define_text_type_strategy(specifier, settings):
    return StringStrategy(strategy([OneCharStringStrategy()], settings))


@strategy.extend_static(binary_type)
def define_binary_strategy(specifier, settings):
    return BinaryStringStrategy(
        strategy=strategy([specifiers.integers_in_range(0, 255)], settings),
    )
