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
import unicodedata

import pytest

from hypothesis import given, settings
from hypothesis.errors import NoExamples
from hypothesis.strategies import strings_matching_regex
from hypothesis.internal.compat import PY3, hrange, hunichr
from hypothesis.searchstrategy.regex import SPACE_CHARS, \
    UNICODE_SPACE_CHARS, HAS_WEIRD_WORD_CHARS, UNICODE_WORD_CATEGORIES, \
    UNICODE_DIGIT_CATEGORIES, UNICODE_SPACE_CATEGORIES, \
    UNICODE_WEIRD_NONWORD_CHARS


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


def is_digit(s):
    return all(unicodedata.category(c) in UNICODE_DIGIT_CATEGORIES for c in s)


def is_space(s):
    return all(c in SPACE_CHARS for c in s)


def is_unicode_space(s):
    return all(
        unicodedata.category(c) in UNICODE_SPACE_CATEGORIES or
        c in UNICODE_SPACE_CHARS
        for c in s
    )


def is_word(s):
    return all(
        c == '_' or (
            (not HAS_WEIRD_WORD_CHARS or
             c not in UNICODE_WEIRD_NONWORD_CHARS) and
            unicodedata.category(c) in UNICODE_WORD_CATEGORIES
        )
        for c in s
    )


def ascii_regex(pattern):
    flags = re.ASCII if PY3 else 0
    return re.compile(pattern, flags)


def unicode_regex(pattern):
    return re.compile(pattern, re.UNICODE)


def _test_matching_pattern(pattern, isvalidchar, is_unicode=False):
    r = unicode_regex(pattern) if is_unicode else ascii_regex(pattern)

    codepoints = hrange(0, sys.maxunicode + 1) \
        if is_unicode else hrange(1, 128)
    for c in [hunichr(x) for x in codepoints]:
        if isvalidchar(c):
            assert r.match(c), (
                '"%s" supposed to match "%s" (%r, category "%s"), '
                'but it doesnt' % (pattern, c, c, unicodedata.category(c))
            )
        else:
            assert not r.match(c), (
                '"%s" supposed not to match "%s" (%r, category "%s"), '
                'but it does' % (pattern, c, c, unicodedata.category(c))
            )


def test_matching_ascii_word_chars():
    _test_matching_pattern(r'\w', is_word)


def test_matching_unicode_word_chars():
    _test_matching_pattern(r'\w', is_word, is_unicode=True)


def test_matching_ascii_non_word_chars():
    _test_matching_pattern(r'\W', lambda s: not is_word(s))


def test_matching_unicode_non_word_chars():
    _test_matching_pattern(r'\W', lambda s: not is_word(s), is_unicode=True)


def test_matching_ascii_digits():
    _test_matching_pattern(r'\d', is_digit)


def test_matching_unicode_digits():
    _test_matching_pattern(r'\d', is_digit, is_unicode=True)


def test_matching_ascii_non_digits():
    _test_matching_pattern(r'\D', lambda s: not is_digit(s))


def test_matching_unicode_non_digits():
    _test_matching_pattern(r'\D', lambda s: not is_digit(s), is_unicode=True)


def test_matching_ascii_spaces():
    _test_matching_pattern(r'\s', is_space)


def test_matching_unicode_spaces():
    _test_matching_pattern(r'\s', is_unicode_space, is_unicode=True)


def test_matching_ascii_non_spaces():
    _test_matching_pattern(r'\S', lambda s: not is_space(s))


def test_matching_unicode_non_spaces():
    _test_matching_pattern(r'\S', lambda s: not is_unicode_space(s),
                           is_unicode=True)


def assert_all_examples(strategy, predicate):
    """Checks that there are no examples with given strategy that do not match
    predicate.

    :param strategy: Hypothesis strategy to check
    :param predicate: (callable) Predicate that takes string example and
        returns bool

    """
    @settings(max_examples=1000, max_iterations=5000)
    @given(strategy)
    def assert_examples(s):
        assert predicate(s), \
            'Found %r using strategy %s which does not match' % (s, strategy)

    assert_examples()


def assert_can_generate(pattern):
    """Checks that regex strategy for given pattern generates examples that
    match that regex pattern."""
    compiled_pattern = re.compile(pattern)
    strategy = strings_matching_regex(pattern)

    assert_all_examples(strategy, compiled_pattern.match)


@pytest.mark.parametrize('pattern', ['a', 'abc', '[a][b][c]'])
def test_literals(pattern):
    assert_can_generate(pattern)


@pytest.mark.parametrize('pattern', [
    re.compile('a', re.IGNORECASE),
    '(?i)a',
    re.compile('[ab]', re.IGNORECASE),
    '(?i)[ab]',
])
def test_literals_with_ignorecase(pattern):
    strategy = strings_matching_regex(pattern)

    strategy.filter(lambda s: s == 'a').example()
    strategy.filter(lambda s: s == 'A').example()


def test_not_literal():
    assert_can_generate('[^a][^b][^c]')


@pytest.mark.parametrize('pattern', [
    re.compile('[^a][^b]', re.IGNORECASE),
    '(?i)[^a][^b]'
])
def test_not_literal_with_ignorecase(pattern):
    assert_all_examples(
        strings_matching_regex(pattern),
        lambda s: s[0] not in ('a', 'A') and s[1] not in ('b', 'B')
    )


def test_any():
    assert_can_generate('.')


def test_any_doesnt_generate_newline():
    assert_all_examples(strings_matching_regex('.'), lambda s: s != '\n')


@pytest.mark.parametrize('pattern', [re.compile('.', re.DOTALL), '(?s).'])
def test_any_with_dotall_generate_newline(pattern):
    strings_matching_regex(pattern).filter(lambda s: s == '\n').example()


def test_range():
    assert_can_generate('[a-z0-9_]')


def test_negative_range():
    assert_can_generate('[^a-z0-9_]')


@pytest.mark.parametrize('pattern', [r'\d', '[\d]', '[^\D]'])
def test_ascii_digits(pattern):
    strategy = strings_matching_regex(ascii_regex(pattern))

    assert_all_examples(strategy, lambda s: is_digit(s) and is_ascii(s))


@pytest.mark.parametrize('pattern', [r'\d', '[\d]', '[^\D]'])
def test_unicode_digits(pattern):
    strategy = strings_matching_regex(unicode_regex(pattern))

    strategy.filter(lambda s: is_digit(s) and is_ascii(s)).example()
    strategy.filter(lambda s: is_digit(s) and not is_ascii(s)).example()

    assert_all_examples(strategy, is_digit)


@pytest.mark.parametrize('pattern', [r'\D', '[\D]', '[^\d]'])
def test_ascii_non_digits(pattern):
    strategy = strings_matching_regex(ascii_regex(pattern))

    assert_all_examples(strategy, lambda s: not is_digit(s) and is_ascii(s))


@pytest.mark.parametrize('pattern', [r'\D', '[\D]', '[^\d]'])
def test_unicode_non_digits(pattern):
    strategy = strings_matching_regex(unicode_regex(pattern))

    strategy.filter(lambda s: not is_digit(s) and is_ascii(s)).example()
    strategy.filter(lambda s: not is_digit(s) and not is_ascii(s)).example()

    assert_all_examples(strategy, lambda s: not is_digit(s))


@pytest.mark.parametrize('pattern', [r'\s', '[\s]', '[^\S]'])
def test_ascii_whitespace(pattern):
    strategy = strings_matching_regex(ascii_regex(pattern))

    assert_all_examples(strategy, lambda s: is_space(s) and is_ascii(s))


@pytest.mark.parametrize('pattern', [r'\s', '[\s]', '[^\S]'])
def test_unicode_whitespace(pattern):
    strategy = strings_matching_regex(unicode_regex(pattern))

    strategy.filter(lambda s: is_unicode_space(s) and is_ascii(s)).example()
    strategy.filter(lambda s: is_unicode_space(s) and not is_ascii(s))\
        .example()

    assert_all_examples(strategy, is_unicode_space)


@pytest.mark.parametrize('pattern', [r'\S', '[\S]', '[^\s]'])
def test_ascii_non_whitespace(pattern):
    strategy = strings_matching_regex(ascii_regex(pattern))

    assert_all_examples(strategy, lambda s: not is_space(s) and is_ascii(s))


@pytest.mark.parametrize('pattern', [r'\S', '[\S]', '[^\s]'])
def test_unicode_non_whitespace(pattern):
    strategy = strings_matching_regex(unicode_regex(pattern))

    strategy.filter(lambda s: not is_unicode_space(s) and is_ascii(s))\
        .example()
    strategy.filter(lambda s: not is_unicode_space(s) and not is_ascii(s))\
        .example()

    assert_all_examples(strategy, lambda s: not is_unicode_space(s))


@pytest.mark.parametrize('pattern', [r'\w', '[\w]', '[^\W]'])
def test_ascii_word(pattern):
    strategy = strings_matching_regex(ascii_regex(pattern))

    assert_all_examples(strategy, lambda s: is_word(s) and is_ascii(s))


@pytest.mark.parametrize('pattern', [r'\w', '[\w]', '[^\W]'])
def test_unicode_word(pattern):
    strategy = strings_matching_regex(unicode_regex(pattern))

    strategy.filter(lambda s: is_word(s) and is_ascii(s)).example()
    strategy.filter(lambda s: is_word(s) and not is_ascii(s)).example()

    assert_all_examples(strategy, is_word)


@pytest.mark.parametrize('pattern', [r'\W', '[\W]', '[^\w]'])
def test_ascii_non_word(pattern):
    strategy = strings_matching_regex(ascii_regex(pattern))

    assert_all_examples(strategy, lambda s: not is_word(s) and is_ascii(s))


@pytest.mark.parametrize('pattern', [r'\W', '[\W]', '[^\w]'])
def test_unicode_non_word(pattern):
    strategy = strings_matching_regex(unicode_regex(pattern))

    strategy.filter(lambda s: not is_word(s) and is_ascii(s)).example()
    strategy.filter(lambda s: not is_word(s) and not is_ascii(s)).example()

    assert_all_examples(strategy, lambda s: not is_word(s))


def test_question_mark_quantifier():
    assert_can_generate('ab?')


def test_asterisk_quantifier():
    assert_can_generate('ab*')


def test_plus_quantifier():
    assert_can_generate('ab+')


def test_repeater():
    assert_can_generate('ab{5}')
    assert_can_generate('ab{5,10}')
    assert_can_generate('ab{,10}')
    assert_can_generate('ab{5,}')


def test_branch():
    assert_can_generate('ab|cd|ef')


def test_group():
    assert_can_generate('(foo)+')


def test_group_backreference():
    assert_can_generate('([\'"])[a-z]+\\1')


def test_non_capturing_group():
    assert_can_generate('(?:[a-z])([\'"])[a-z]+\\1')


def test_named_groups():
    assert_can_generate('(?P<foo>[\'"])[a-z]+(?P=foo)')


def test_begining():
    assert_can_generate('^abc')


def test_caret_in_the_middle_does_not_generate_anything():
    r = re.compile('a^b')

    with pytest.raises(NoExamples):
        strings_matching_regex(r).filter(r.match).example()


def test_end():
    strategy = strings_matching_regex('abc$')

    strategy.filter(lambda s: s == 'abc').example()
    strategy.filter(lambda s: s == 'abc\n').example()


def test_groupref_exists():
    assert_all_examples(
        strings_matching_regex('^(<)?a(?(1)>)$'),
        lambda s: s in ('a', 'a\n', '<a>', '<a>\n')
    )
    assert_all_examples(
        strings_matching_regex('^(a)?(?(1)b|c)$'),
        lambda s: s in ('ab', 'ab\n', 'c', 'c\n')
    )


def test_positive_lookbehind():
    strings_matching_regex('.*(?<=ab)c').filter(lambda s: s.endswith('abc'))\
        .example()


def test_positive_lookahead():
    strings_matching_regex('a(?=bc).*').filter(lambda s: s.startswith('abc'))\
        .example()


def test_negative_lookbehind():
    # no efficient support
    strategy = strings_matching_regex('[abc]*(?<!abc)d')

    assert_all_examples
    with pytest.raises(NoExamples):
        strategy.filter(lambda s: s.endswith('abcd')).example()


def test_negative_lookahead():
    # no efficient support
    strategy = strings_matching_regex('ab(?!cd)[abcd]*')

    assert_all_examples
    with pytest.raises(NoExamples):
        strategy.filter(lambda s: s.startswith('abcd')).example()


@pytest.mark.skipif(sys.version_info[:2] < (3, 6),
                    reason='requires Python 3.6')
def test_subpattern_flags():
    strategy = strings_matching_regex('(?i)a(?-i:b)')

    # "a" is case insensitive
    strategy.filter(lambda s: s[0] == 'a').example()
    strategy.filter(lambda s: s[0] == 'A').example()
    # "b" is case sensitive
    strategy.filter(lambda s: s[1] == 'b').example()

    with pytest.raises(NoExamples):
        strategy.filter(lambda s: s[1] == 'B').example()
