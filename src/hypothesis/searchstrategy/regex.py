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

import hypothesis.strategies as st
from hypothesis import reject
from hypothesis.internal.compat import PY3, hrange, hunichr, text_type, \
    int_to_byte

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

# This is verbose, but correct on all versions of Python
BYTES_ALL = set(int_to_byte(i) for i in range(256))
BYTES_DIGIT = set(b for b in BYTES_ALL if re.match(b'\\d', b))
BYTES_SPACE = set(b for b in BYTES_ALL if re.match(b'\\s', b))
BYTES_WORD = set(b for b in BYTES_ALL if re.match(b'\\w', b))
BYTES_LOOKUP = {
    sre.CATEGORY_DIGIT: BYTES_DIGIT,
    sre.CATEGORY_SPACE: BYTES_SPACE,
    sre.CATEGORY_WORD: BYTES_WORD,
    sre.CATEGORY_NOT_DIGIT: BYTES_ALL - BYTES_DIGIT,
    sre.CATEGORY_NOT_SPACE: BYTES_ALL - BYTES_SPACE,
    sre.CATEGORY_NOT_WORD: BYTES_ALL - BYTES_WORD,
}

# On Python < 3.4 (including 2.7), the following unicode chars are weird.
# They are matched by the \W, meaning 'not word', but unicodedata.category(c)
# returns one of the word categories above.  There's special handling below.
HAS_WEIRD_WORD_CHARS = sys.version_info[:2] < (3, 4)
UNICODE_WEIRD_NONWORD_CHARS = set(u'\U00012432\U00012433\U00012456\U00012457')


GROUP_CACHE_STRATEGY = st.shared(
    st.builds(dict), key='hypothesis.regex.group_cache'
)


@st.composite
def update_group(draw, group_name, strategy):
    cache = draw(GROUP_CACHE_STRATEGY)
    result = draw(strategy)
    cache[group_name] = result
    return result


@st.composite
def reuse_group(draw, group_name):
    cache = draw(GROUP_CACHE_STRATEGY)
    try:
        return cache[group_name]
    except KeyError:
        reject()


@st.composite
def group_conditional(draw, group_name, if_yes, if_no):
    cache = draw(GROUP_CACHE_STRATEGY)
    if group_name in cache:
        return draw(if_yes)
    else:
        return draw(if_no)


@st.composite
def clear_cache_after_draw(draw, base_strategy):
    cache = draw(GROUP_CACHE_STRATEGY)
    result = draw(base_strategy)
    cache.clear()
    return result


class Context(object):
    __slots__ = ['flags']

    def __init__(self, groups=None, flags=0):
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
        self.code_to_char = hunichr

    @property
    def strategy(self):
        """Returns resulting strategy that generates configured char set."""
        max_codepoint = None if self._unicode else 127
        if self._negate:
            black_chars = self._blacklist_chars - self._whitelist_chars
            return st.characters(
                blacklist_categories=self._categories | {'Cc', 'Cs'},
                blacklist_characters=self._whitelist_chars,
                whitelist_characters=black_chars,
                max_codepoint=max_codepoint,
            )
        white_chars = self._whitelist_chars - self._blacklist_chars
        return st.characters(
            whitelist_categories=self._categories,
            blacklist_characters=self._blacklist_chars,
            whitelist_characters=white_chars,
            max_codepoint=max_codepoint,
        )

    def add_category(self, category):
        """Update unicode state to match sre_parse object ``category``."""
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
        elif category == sre.CATEGORY_NOT_WORD:
            self._categories |= UNICODE_CATEGORIES - UNICODE_WORD_CATEGORIES
            self._blacklist_chars.add(u'_')
            if HAS_WEIRD_WORD_CHARS and self._unicode:  # pragma: no cover
                # This code is workaround of weird behavior in
                # specific Python versions and run only on those versions
                self._whitelist_chars |= UNICODE_WEIRD_NONWORD_CHARS
        else:  # pragma: no cover
            raise AssertionError('Unknown character category: %s' % category)

    def add_char(self, char):
        """Add given char to the whitelist."""
        c = self.code_to_char(char)
        self._whitelist_chars.add(c)
        if self._ignorecase and \
                re.match(c, c.swapcase(), re.IGNORECASE) is not None:
            self._whitelist_chars.add(c.swapcase())


class BytesBuilder(CharactersBuilder):

    def __init__(self, negate=False, flags=0):
        self._whitelist_chars = set()
        self._blacklist_chars = set()
        self._negate = negate
        self._ignorecase = flags & re.IGNORECASE
        self.code_to_char = int_to_byte

    @property
    def strategy(self):
        """Returns resulting strategy that generates configured char set."""
        allowed = self._whitelist_chars
        if self._negate:
            allowed = BYTES_ALL - allowed
        return st.sampled_from(sorted(allowed))

    def add_category(self, category):
        """Update characters state to match sre_parse object ``category``."""
        self._whitelist_chars |= BYTES_LOOKUP[category]


@st.composite
def maybe_pad(draw, regex, strategy):
    """Attempt to insert padding around the result of a regex draw while
    preserving the match."""
    if not regex.pattern:
        if isinstance(regex.pattern, text_type):
            return draw(st.text())
        else:
            return draw(st.binary())

    result = draw(strategy)

    if isinstance(regex.pattern, text_type):
        padding_strategy = st.text(average_size=1)
    else:
        padding_strategy = st.binary(average_size=1)

    # We check the pattern for starting with ^ as a simple optimisation.
    # Correctness is not affected, but we draw less data this way. It is
    # possible to defeat this check quite easily, but it optimises for the
    # happy case.
    if regex.pattern[0] not in (b'^', u'^'):
        pad_left = draw(padding_strategy)
        if regex.search(pad_left + result):
            result = pad_left + result

    # Similarly to above, we check if the pattern obviously ends with a $ and
    # skip the right padding if it does.
    if regex.pattern[-1] not in (b'$', u'$'):
        pad_right = draw(padding_strategy)
        if regex.search(result + pad_right):
            result += pad_right

    return result


def base_regex_strategy(regex):
    return clear_cache_after_draw(_strategy(
        sre.parse(regex.pattern),
        Context(flags=regex.flags),
        regex.pattern
    ))


def regex_strategy(regex):
    if not hasattr(regex, 'pattern'):
        regex = re.compile(regex)
    return maybe_pad(
        regex,
        base_regex_strategy(regex).filter(regex.search))


def _strategy(codes, context, pattern):
    """Convert SRE regex parse tree to strategy that generates strings matching
    that regex represented by that parse tree.

    `codes` is either a list of SRE regex elements representations or a
    particular element representation. Each element is a tuple of element code
    (as string) and parameters. E.g. regex 'ab[0-9]+' compiles to following
    elements:

        [
            (LITERAL, 97),
            (LITERAL, 98),
            (MAX_REPEAT, (1, 4294967295, [
                (IN, [
                    (RANGE, (48, 57))
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
    def recurse(codes):
        return _strategy(codes, context, pattern)

    if isinstance(pattern, text_type):
        empty = u''
        to_char = hunichr
    else:
        empty = b''
        to_char = int_to_byte
        binary_char = st.binary(min_size=1, max_size=1)

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
                    strategies.append(st.just(
                        empty.join([to_char(charcode)
                                    for (_, charcode) in codes[i:j]])
                    ))

                    i = j
                    continue

            strategies.append(recurse(codes[i]))
            i += 1

        if not strategies:
            return st.just(empty)
        if len(strategies) == 1:
            return strategies[0]
        return st.tuples(*strategies).map(empty.join)
    else:
        # Single code
        code, value = codes
        if code == sre.LITERAL:
            # Regex 'a' (single char)
            c = to_char(value)
            if context.flags & re.IGNORECASE and \
                    re.match(c, c.swapcase(), re.IGNORECASE) is not None:
                # We do the explicit check for swapped-case matching because
                # eg 'ß'.upper() == 'SS' and ignorecase doesn't match it.
                return st.sampled_from([c, c.swapcase()])
            return st.just(c)

        elif code == sre.NOT_LITERAL:
            # Regex '[^a]' (negation of a single char)
            c = to_char(value)
            blacklist = set(c)
            if context.flags & re.IGNORECASE and \
                    re.match(c, c.swapcase(), re.IGNORECASE) is not None:
                blacklist |= set(c.swapcase())
            if isinstance(pattern, text_type):
                return st.characters(blacklist_characters=blacklist)
            else:
                return binary_char.filter(lambda c: c not in blacklist)

        elif code == sre.IN:
            # Regex '[abc0-9]' (set of characters)
            negate = value[0][0] == sre.NEGATE
            if isinstance(pattern, text_type):
                builder = CharactersBuilder(negate, context.flags)
            else:
                builder = BytesBuilder(negate, context.flags)

            for charset_code, charset_value in value:
                if charset_code == sre.NEGATE:
                    # Regex '[^...]' (negation)
                    # handled by builder = CharactersBuilder(...) above
                    pass
                elif charset_code == sre.LITERAL:
                    # Regex '[a]' (single char)
                    builder.add_char(charset_value)
                elif charset_code == sre.RANGE:
                    # Regex '[a-z]' (char range)
                    low, high = charset_value
                    for char_code in hrange(low, high + 1):
                        builder.add_char(char_code)
                elif charset_code == sre.CATEGORY:
                    # Regex '[\w]' (char category)
                    builder.add_category(charset_value)
                else:  # pragma: no cover
                    # Currently there are no known code points other than
                    # handled here. This code is just future proofing
                    raise AssertionError('Unknown charset code: %s'
                                         % charset_code)
            return builder.strategy

        elif code == sre.ANY:
            # Regex '.' (any char)
            if isinstance(pattern, text_type):
                if context.flags & re.DOTALL:
                    return st.characters()
                return st.characters(blacklist_characters=u'\n')
            else:
                if context.flags & re.DOTALL:
                    return binary_char
                return binary_char.filter(lambda c: c != b'\n')

        elif code == sre.AT:
            # Regexes like '^...', '...$', '\bfoo', '\Bfoo'
            # An empty string (or newline) will match the token itself, but
            # we don't and can't check the position (eg '%' at the end)
            return st.just(empty)

        elif code == sre.SUBPATTERN:
            # Various groups: '(...)', '(:...)' or '(?P<name>...)'
            old_flags = context.flags
            if HAS_SUBPATTERN_FLAGS:  # pragma: no cover
                # This feature is available only in specific Python versions
                context.flags = (context.flags | value[1]) & ~value[2]

            strat = _strategy(value[-1], context, pattern)

            context.flags = old_flags

            if value[0]:
                strat = update_group(value[0], strat)

            return strat

        elif code == sre.GROUPREF:
            # Regex '\\1' or '(?P=name)' (group reference)
            return reuse_group(value)

        elif code == sre.ASSERT:
            # Regex '(?=...)' or '(?<=...)' (positive lookahead/lookbehind)
            return recurse(value[1])

        elif code == sre.ASSERT_NOT:
            # Regex '(?!...)' or '(?<!...)' (negative lookahead/lookbehind)
            return st.just(empty)

        elif code == sre.BRANCH:
            # Regex 'a|b|c' (branch)
            return st.one_of([recurse(branch) for branch in value[1]])

        elif code in [sre.MIN_REPEAT, sre.MAX_REPEAT]:
            # Regexes 'a?', 'a*', 'a+' and their non-greedy variants
            # (repeaters)
            at_least, at_most, subregex = value
            if at_most == sre.MAXREPEAT:
                at_most = None
            if at_least == 0 and at_most == 1:
                return st.just(empty) | recurse(subregex)
            return st.lists(recurse(subregex),
                            min_size=at_least,
                            max_size=at_most).map(empty.join)

        elif code == sre.GROUPREF_EXISTS:
            # Regex '(?(id/name)yes-pattern|no-pattern)'
            # (if group exists choice)
            return group_conditional(
                value[0],
                recurse(value[1]),
                recurse(value[2]) if value[2] else st.just(empty),
            )

        else:  # pragma: no cover
            # Currently there are no known code points other than handled here.
            # This code is just future proofing
            raise AssertionError('Unknown code point: %s' % repr(code))
