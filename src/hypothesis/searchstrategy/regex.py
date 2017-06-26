# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

import re
import sys
import sre_parse as sre

import hypothesis.strategies as hs
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import PY3, hrange, hunichr

HAS_SUBPATTERN_FLAGS = sys.version_info[:2] >= (3, 6)


UNICODE_CATEGORIES = set([
    'Cf', 'Cn', 'Co', 'LC', 'Ll', 'Lm', 'Lo', 'Lt', 'Lu',
    'Mc', 'Me', 'Mn', 'Nd', 'Nl', 'No', 'Pc', 'Pd', 'Pe',
    'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zl',
    'Zp', 'Zs',
])


SPACE_CHARS = set(u' \t\n\r\f\v')
UNICODE_SPACE_CHARS = SPACE_CHARS | set(u'\x1c\x1d\x1e\x1f\x85')
UNICODE_DIGIT_CATEGORIES = set(['Nd'])
UNICODE_SPACE_CATEGORIES = set(['Zs', 'Zl', 'Zp'])
UNICODE_LETTER_CATEGORIES = set(['LC', 'Ll', 'Lm', 'Lo', 'Lt', 'Lu'])
UNICODE_WORD_CATEGORIES = UNICODE_LETTER_CATEGORIES | set(['Nd', 'Nl', 'No'])

# On Python >= 3.0 and < 3.4 particular unicode word chars are not
# considered as word chars, thus not matched by "\w" category in regex
HAS_WEIRD_WORD_CHARS = (2, 7) <= sys.version_info[:2] < (3, 4)
UNICODE_WEIRD_NONWORD_CHARS = set(u'\U00012432\U00012433\U00012456\U00012457')


class Context(object):
    __slots__ = ['groups', 'flags']

    def __init__(self, groups=None, flags=0):
        self.groups = groups or {}
        self.flags = flags


class CharactersBuilder(object):
    """Helper object that allows to configure `characters` strategy with
    various unicode categories and characters. Also allows negation of
    configured set.

    :param negate: If True, configure :func:`hypothesis.strategies.characters`
        to match anything other than configured character set
    :param flags: Regex flags. They affect how and which characters are matched

    """

    def __init__(self, negate=False, flags=0):
        self._categories = set()
        self._whitelist_chars = set()
        self._blacklist_chars = set()
        self._negate = negate
        self._ignorecase = flags & re.IGNORECASE
        self._unicode = not bool(flags & re.ASCII) \
            if PY3 else bool(flags & re.UNICODE)

    @property
    def strategy(self):
        """Returns resulting strategy that generates configured char set."""
        max_codepoint = None if self._unicode else 127

        strategies = []
        if self._negate:
            if self._categories or self._whitelist_chars:  # pragma: no branch
                strategies.append(
                    hs.characters(
                        blacklist_categories=self._categories | set(
                            ['Cc', 'Cs']),
                        blacklist_characters=self._whitelist_chars,
                        max_codepoint=max_codepoint,
                    )
                )
            if self._blacklist_chars:
                strategies.append(
                    hs.sampled_from(
                        sorted(self._blacklist_chars - self._whitelist_chars)
                    )
                )
        else:
            if self._categories or self._blacklist_chars:
                strategies.append(
                    hs.characters(
                        whitelist_categories=self._categories,
                        blacklist_characters=self._blacklist_chars,
                        max_codepoint=max_codepoint,
                    )
                )
            if self._whitelist_chars:
                strategies.append(
                    hs.sampled_from(
                        sorted(self._whitelist_chars - self._blacklist_chars)
                    )
                )

        return hs.one_of(*strategies) if strategies else hs.just(u'')

    def add_category(self, category):
        """Add unicode category to set.

        Unicode categories are strings like 'Ll', 'Lu', 'Nd', etc. See
        `unicodedata.category()`

        """
        if category == sre.CATEGORY_DIGIT:
            self._categories |= UNICODE_DIGIT_CATEGORIES
        elif category == sre.CATEGORY_NOT_DIGIT:
            self._categories |= UNICODE_CATEGORIES - UNICODE_DIGIT_CATEGORIES
        elif category == sre.CATEGORY_SPACE:
            self._categories |= UNICODE_SPACE_CATEGORIES
            self._whitelist_chars |= UNICODE_SPACE_CHARS \
                if self._unicode else SPACE_CHARS
        elif category == sre.CATEGORY_NOT_SPACE:
            self._categories |= UNICODE_CATEGORIES - UNICODE_SPACE_CATEGORIES
            self._blacklist_chars |= UNICODE_SPACE_CHARS \
                if self._unicode else SPACE_CHARS
        elif category == sre.CATEGORY_WORD:
            self._categories |= UNICODE_WORD_CATEGORIES
            self._whitelist_chars.add(u'_')
            if HAS_WEIRD_WORD_CHARS and self._unicode:  # pragma: no cover
                # This code is workaround of weird behavior in
                # specific Python versions and run only on those versions
                self._blacklist_chars |= UNICODE_WEIRD_NONWORD_CHARS
        elif category == sre.CATEGORY_NOT_WORD:  # pragma: no branch
            self._categories |= UNICODE_CATEGORIES - UNICODE_WORD_CATEGORIES
            self._blacklist_chars.add(u'_')
            if HAS_WEIRD_WORD_CHARS and self._unicode:  # pragma: no cover
                # This code is workaround of weird behavior in
                # specific Python versions and run only on those versions
                self._whitelist_chars |= UNICODE_WEIRD_NONWORD_CHARS
        else:  # pragma: no cover
            raise InvalidArgument(
                'Unknown character category: %s' % category
            )

    def add_chars(self, chars):
        """Add given chars to char set."""
        for c in chars:
            if self._ignorecase:
                self._whitelist_chars.add(c.lower())
                self._whitelist_chars.add(c.upper())
            else:
                self._whitelist_chars.add(c)


def regex_strategy(regex):
    if not hasattr(regex, 'pattern'):
        regex = re.compile(regex)

    pattern = regex.pattern
    flags = regex.flags

    codes = sre.parse(pattern)

    return _strategy(codes, Context(flags=flags)).filter(regex.match)


def _strategy(codes, context):
    """Convert SRE regex parse tree to strategy that generates strings matching
    that regex represented by that parse tree.

    `codes` is either a list of SRE regex elements representations or a
    particular element representation. Each element is a tuple of element code
    (as string) and parameters. E.g. regex 'ab[0-9]+' compiles to following
    elements:

        [
            ('literal', 97),
            ('literal', 98),
            ('max_repeat', (1, 4294967295, [
                ('in', [
                    ('range', (48, 57))
                ])
            ]))
        ]

    The function recursively traverses regex element tree and converts each
    element to strategy that generates strings that match that element.

    Context stores
    1. List of groups (for backreferences)
    2. Active regex flags (e.g. IGNORECASE, DOTALL, UNICODE, they affect
       behavior of various inner strategies)

    """
    if not isinstance(codes, tuple):
        # List of codes
        strategies = []

        i = 0
        while i < len(codes):
            if codes[i][0] == sre.LITERAL and \
                    not context.flags & re.IGNORECASE:
                # Merge subsequent "literals" into one `just()` strategy
                # that generates corresponding text if no IGNORECASE
                j = i + 1
                while j < len(codes) and codes[j][0] == sre.LITERAL:
                    j += 1

                if i + 1 < j:
                    strategies.append(hs.just(
                        u''.join([hunichr(charcode)
                                  for (_, charcode) in codes[i:j]])
                    ))

                    i = j
                    continue

            strategies.append(_strategy(codes[i], context))
            i += 1

        return hs.tuples(*strategies).map(u''.join)
    else:
        # Single code
        code, value = codes
        if code == sre.LITERAL:
            # Regex 'a' (single char)
            c = hunichr(value)
            if context.flags & re.IGNORECASE:
                return hs.sampled_from([c.lower(), c.upper()])

            return hs.just(c)

        elif code == sre.NOT_LITERAL:
            # Regex '[^a]' (negation of a single char)
            c = hunichr(value)
            blacklist = set([c.lower(), c.upper()]) \
                if context.flags & re.IGNORECASE else [c]
            return hs.characters(blacklist_characters=blacklist)

        elif code == sre.IN:
            # Regex '[abc0-9]' (set of characters)
            charsets = value

            builder = CharactersBuilder(negate=charsets[0][0] == sre.NEGATE,
                                        flags=context.flags)

            for charset_code, charset_value in charsets:
                if charset_code == sre.NEGATE:
                    # Regex '[^...]' (negation)
                    pass
                elif charset_code == sre.LITERAL:
                    # Regex '[a]' (single char)
                    builder.add_chars(hunichr(charset_value))
                elif charset_code == sre.RANGE:
                    # Regex '[a-z]' (char range)
                    low, high = charset_value
                    for char_code in hrange(low, high + 1):
                        builder.add_chars(hunichr(char_code))
                elif charset_code == sre.CATEGORY:
                    # Regex '[\w]' (char category)
                    builder.add_category(charset_value)
                else:  # pragma: no cover
                    # Currently there are no known code points other than
                    # handled here. This code is just future proofing
                    raise InvalidArgument(
                        'Unknown charset code: %s' % charset_code
                    )

            return builder.strategy

        elif code == sre.ANY:
            # Regex '.' (any char)
            if context.flags & re.DOTALL:
                return hs.characters()

            return hs.characters(blacklist_characters='\n')

        elif code == sre.AT:
            # Regexes like '^...', '...$', '\bfoo', '\Bfoo'
            if value == sre.AT_END:
                return hs.one_of(hs.just(u''), hs.just(u'\n'))
            return hs.just('')

        elif code == sre.SUBPATTERN:
            # Various groups: '(...)', '(:...)' or '(?P<name>...)'
            old_flags = context.flags
            if HAS_SUBPATTERN_FLAGS:  # pragma: no cover
                # This feature is available only in specific Python versions
                context.flags = (context.flags | value[1]) & ~value[2]

            strat = _strategy(value[-1], context)

            context.flags = old_flags

            if value[0]:
                context.groups[value[0]] = strat
                strat = hs.shared(strat, key=value[0])

            return strat

        elif code == sre.GROUPREF:
            # Regex '\\1' or '(?P=name)' (group reference)
            return hs.shared(context.groups[value], key=value)

        elif code == sre.ASSERT:
            # Regex '(?=...)' or '(?<=...)' (positive lookahead/lookbehind)
            return _strategy(value[1], context)

        elif code == sre.ASSERT_NOT:
            # Regex '(?!...)' or '(?<!...)' (negative lookahead/lookbehind)
            return hs.just('')

        elif code == sre.BRANCH:
            # Regex 'a|b|c' (branch)
            return hs.one_of([_strategy(branch, context)
                              for branch in value[1]])

        elif code in [sre.MIN_REPEAT, sre.MAX_REPEAT]:
            # Regexes 'a?', 'a*', 'a+' and their non-greedy variants
            # (repeaters)
            at_least, at_most, subregex = value
            if at_most == sre.MAXREPEAT:
                at_most = None
            return hs.lists(_strategy(subregex, context),
                            min_size=at_least,
                            max_size=at_most).map(''.join)

        elif code == sre.GROUPREF_EXISTS:
            # Regex '(?(id/name)yes-pattern|no-pattern)'
            # (if group exists choice)
            return hs.one_of(
                _strategy(value[1], context),
                _strategy(value[2], context) if value[2] else hs.just(u''),
            )

        else:  # pragma: no cover
            # Currently there are no known code points other than handled here.
            # This code is just future proofing
            raise InvalidArgument('Unknown code point: %s' % repr(code))
