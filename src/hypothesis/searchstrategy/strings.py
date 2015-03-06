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
import string
import unicodedata

import hypothesis.descriptors as descriptors
import hypothesis.internal.distributions as dist
from hypothesis.internal.compat import hrange, hunichr, text_type, \
    binary_type
from hypothesis.searchstrategy.strategies import BadData, SearchStrategy, \
    MappedSearchStrategy, strategy, check_type, check_data_type


class OneCharStringStrategy(SearchStrategy):

    """A strategy which generates single character strings of text type."""
    descriptor = text_type
    ascii_characters = (
        text_type('0123456789') + text_type(string.ascii_letters) +
        text_type(' \t\n')
    )

    def produce_parameter(self, random):
        return random.random()

    def produce_template(self, context, p):
        random = context.random
        if dist.biased_coin(random, p):
            return random.choice(self.ascii_characters)
        else:
            while True:
                result = hunichr(random.randint(0, sys.maxunicode))
                if unicodedata.category(result) != 'Cs':
                    return result

    def simplify(self, x):
        if x in self.ascii_characters:
            for i in hrange(self.ascii_characters.index(x) - 1, -1, -1):
                yield self.ascii_characters[i]
        else:
            o = ord(x)
            for c in reversed(self.ascii_characters):
                yield text_type(c)
            yield hunichr(o // 2)
            for t in hrange(o - 1, -1, -1):
                yield hunichr(t)


class StringStrategy(MappedSearchStrategy):

    """A strategy for text strings, defined in terms of a strategy for lists of
    single character text strings."""

    def __init__(self, list_of_one_char_strings_strategy):
        super(StringStrategy, self).__init__(
            descriptor=text_type,
            strategy=list_of_one_char_strings_strategy
        )

    def pack(self, ls):
        return ''.join(ls)

    def decompose(self, value):
        return ()

    def to_basic(self, c):
        check_type(tuple, c)
        return ''.join(c)

    def from_basic(self, c):
        check_data_type(text_type, c)
        return tuple(c)


class BinaryStringStrategy(MappedSearchStrategy):

    """A strategy for strings of bytes, defined in terms of a strategy for
    lists of bytes."""

    def pack(self, x):
        assert isinstance(x, list), repr(x)
        ba = bytearray(x)
        return binary_type(ba)

    def decompose(self, value):
        return ()

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


@strategy.extend_static(text_type)
def define_text_type_strategy(descriptor, settings):
    return StringStrategy(strategy([OneCharStringStrategy()], settings))


@strategy.extend_static(binary_type)
def define_binary_strategy(descriptor, settings):
    return BinaryStringStrategy(
        strategy=strategy([descriptors.integers_in_range(0, 255)], settings),
        descriptor=binary_type,
    )
