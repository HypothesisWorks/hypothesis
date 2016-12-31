# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import sys
from array import array

from hypothesis.errors import InvalidArgument
from hypothesis.internal import charmap
from hypothesis.internal.compat import hunichr, text_type, bit_length, \
    binary_type, int_to_bytes, int_from_bytes
from hypothesis.searchstrategy.strategies import SearchStrategy, \
    MappedSearchStrategy
from hypothesis.internal.conjecture.grammar import Literal, Interval, \
    Negation, Wildcard, Alternation, Intersection

N_BYTES_FOR_CODEPOINT = (
    bit_length(sys.maxunicode) // 8 + int(bit_length(sys.maxunicode) % 8 != 0)
)


def codepoint_interval(lower, upper):
    return Interval(
        int_to_bytes(lower, N_BYTES_FOR_CODEPOINT),
        int_to_bytes(upper, N_BYTES_FOR_CODEPOINT),
    )


ANY_CODEPOINT = codepoint_interval(0, sys.maxunicode)

CATEGORY_GRAMMARS = {}


def category_grammar(category):
    try:
        return CATEGORY_GRAMMARS[category]
    except KeyError:
        pass
    result = Alternation([
        codepoint_interval(i, j)
        for i, j in charmap.charmap()[category]
    ])
    CATEGORY_GRAMMARS[category] = result
    return result


class OneCharStringStrategy(SearchStrategy):

    """A strategy which generates single character strings of text type."""
    specifier = text_type
    zero_point = ord('0')

    def __init__(self,
                 whitelist_categories=None,
                 blacklist_categories=None,
                 blacklist_characters=None,
                 min_codepoint=None,
                 max_codepoint=None):

        categories = tuple(charmap.categories())
        if whitelist_categories is not None:
            categories = tuple(
                c for c in categories if c in whitelist_categories)
        if blacklist_categories is not None:
            categories = tuple(
                c for c in categories if c not in blacklist_categories)

        grammars_by_category = tuple(category_grammar(c) for c in categories)
        grammars_by_category = tuple(category_grammar(c) for c in categories)

        base_grammar = Alternation(grammars_by_category)

        if blacklist_characters is not None:
            base_grammar = Intersection([base_grammar] + [
                Negation(Literal(int_to_bytes(ord(v), N_BYTES_FOR_CODEPOINT)))
                for v in blacklist_characters
            ])

        if min_codepoint is not None or max_codepoint is not None:
            base_grammar = Intersection([
                base_grammar,
                codepoint_interval(
                    min_codepoint or 0, max_codepoint or sys.maxunicode)])

        if not base_grammar.has_matches():
            raise InvalidArgument('No valid characters in set')

        grammars_by_category = tuple(
            Intersection([g, base_grammar])
            for g in grammars_by_category
        )
        grammars_by_category = tuple(
            g for g in grammars_by_category
            if g.has_matches()
        )

        shrinking_grammars = [
            Intersection([
                codepoint_interval(ord('0') - i, sys.maxunicode),
                base_grammar])
            for i in range(ord('0'))
        ]
        shrinking_grammars.append(base_grammar),

        shrinking_grammars = tuple(
            c for c in shrinking_grammars if c.has_matches())

        self.grammars = list(shrinking_grammars + grammars_by_category)
        self.weights = array('d', (1,) * len(shrinking_grammars) + (
            len(shrinking_grammars),) * len(grammars_by_category))

        newline = int_to_bytes(ord(b'\n'), N_BYTES_FOR_CODEPOINT)
        if base_grammar.matches(newline):
            # If newlines are permitted we create a bias to generate multi
            # line strings more often - about 10% of characters should be
            # newlines.
            self.grammars.append(Literal(newline))
            self.weights.append(sum(self.weights) * 0.1 / 1.1)
        assert len(self.grammars) == len(self.weights)

    def do_draw(self, data):
        i = data.draw_byte(self.weights)
        c = int_from_bytes(data.draw_from_grammar(self.grammars[i]))
        assert 0 <= c <= sys.maxunicode, c
        return hunichr(c)


class StringStrategy(MappedSearchStrategy):

    """A strategy for text strings, defined in terms of a strategy for lists of
    single character text strings."""

    def __init__(self, list_of_one_char_strings_strategy):
        super(StringStrategy, self).__init__(
            strategy=list_of_one_char_strings_strategy
        )

    def __repr__(self):
        return 'StringStrategy(%r)' % (
            self.mapped_strategy,
        )

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


class FixedSizeBytes(SearchStrategy):

    def __init__(self, size):
        self.grammar = Wildcard(size)

    def do_draw(self, data):
        return data.draw_from_grammar(self.grammar)
