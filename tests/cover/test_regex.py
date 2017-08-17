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

from hypothesis import given, assume, reject
from hypothesis.errors import NoExamples, FailedHealthCheck
from hypothesis.strategies import data, text, binary, tuples, from_regex
from hypothesis.internal.compat import PY3, hrange, hunichr, text_type
from hypothesis.searchstrategy.regex import SPACE_CHARS, \
    UNICODE_SPACE_CHARS, HAS_WEIRD_WORD_CHARS, UNICODE_WORD_CATEGORIES, \
    UNICODE_DIGIT_CATEGORIES, UNICODE_SPACE_CATEGORIES, \
    UNICODE_WEIRD_NONWORD_CHARS, base_regex_strategy


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


@pytest.mark.parametrize('category,predicate', [
    (r'\w', is_word), (r'\d', is_digit), (r'\s', None)])
@pytest.mark.parametrize('invert', [False, True])
@pytest.mark.parametrize('is_unicode', [False, True])
def test_matching(category, predicate, invert, is_unicode):
    if predicate is None:
        # Special behaviour due to \x1c, INFORMATION SEPARATOR FOUR
        predicate = is_unicode_space if is_unicode else is_space
    pred = predicate
    if invert:
        category = category.swapcase()

        def pred(s):
            return not predicate(s)

    _test_matching_pattern(category, pred, is_unicode)


def assert_all_examples(strategy, predicate):
    """Checks that there are no examples with given strategy that do not match
    predicate.

    :param strategy: Hypothesis strategy to check
    :param predicate: (callable) Predicate that takes string example and
        returns bool

    """
    @given(strategy)
    def assert_examples(s):
        assert predicate(s), \
            'Found %r using strategy %s which does not match' % (s, strategy)

    assert_examples()


@pytest.mark.parametrize('pattern', [
    u'.',  # anything
    u'a', u'abc', u'[a][b][c]', u'[^a][^b][^c]',  # literals
    u'[a-z0-9_]', u'[^a-z0-9_]',  # range and negative range
    u'ab?', u'ab*', u'ab+',  # quantifiers
    u'ab{5}', u'ab{5,10}', u'ab{,10}', u'ab{5,}',  # repeaters
    u'ab|cd|ef',  # branch
    u'(foo)+', u'([\'"])[a-z]+\\1',
    u'(?:[a-z])([\'"])[a-z]+\\1', u'(?P<foo>[\'"])[a-z]+(?P=foo)',  # groups
    u'^abc',  # beginning
    u'\d', u'[\d]', u'[^\D]', u'\w', u'[\w]', u'[^\W]',
    u'\s', u'[\s]', u'[^\S]',  # categories
])
@pytest.mark.parametrize('encode', [False, True])
def test_can_generate(pattern, encode):
    if encode:
        pattern = pattern.encode('ascii')
    assert_all_examples(from_regex(pattern), re.compile(pattern).match)


@pytest.mark.parametrize('pattern', [
    re.compile(u'a', re.IGNORECASE),
    u'(?i)a',
    re.compile(u'[ab]', re.IGNORECASE),
    u'(?i)[ab]',
])
def test_literals_with_ignorecase(pattern):
    strategy = from_regex(pattern)

    strategy.filter(lambda s: s == u'a').example()
    strategy.filter(lambda s: s == u'A').example()


@pytest.mark.parametrize('pattern', [
    re.compile(u'[^a][^b]', re.IGNORECASE),
    u'(?i)[^a][^b]'
])
def test_not_literal_with_ignorecase(pattern):
    assert_all_examples(
        from_regex(pattern),
        lambda s: s[0] not in (u'a', u'A') and s[1] not in (u'b', u'B')
    )


def test_any_doesnt_generate_newline():
    assert_all_examples(from_regex(u'.'), lambda s: s != u'\n')


@pytest.mark.parametrize('pattern', [re.compile(u'.', re.DOTALL), u'(?s).'])
def test_any_with_dotall_generate_newline(pattern):
    from_regex(pattern).filter(lambda s: s == u'\n').example()


@pytest.mark.parametrize('pattern', [re.compile(b'.', re.DOTALL), b'(?s).'])
def test_any_with_dotall_generate_newline_binary(pattern):
    from_regex(pattern).filter(lambda s: s == b'\n').example()


@pytest.mark.parametrize('pattern', [
    u'\d', u'[\d]', u'[^\D]',
    u'\w', u'[\w]', u'[^\W]',
    u'\s', u'[\s]', u'[^\S]',
])
@pytest.mark.parametrize('is_unicode', [False, True])
@pytest.mark.parametrize('invert', [False, True])
def test_groups(pattern, is_unicode, invert):
    if u'd' in pattern.lower():
        group_pred = is_digit
    elif u'w' in pattern.lower():
        group_pred = is_word
    else:
        # Special behaviour due to \x1c, INFORMATION SEPARATOR FOUR
        group_pred = is_unicode_space if is_unicode else is_space

    if invert:
        pattern = pattern.swapcase()
        _p = group_pred

        def group_pred(s):
            return not _p(s)

    compiler = unicode_regex if is_unicode else ascii_regex
    strategy = from_regex(compiler(pattern))

    strategy.filter(group_pred).filter(is_ascii).example()
    if is_unicode:
        strategy.filter(lambda s: group_pred(s) and not is_ascii(s)).example()

    assert_all_examples(strategy, group_pred)


def test_caret_in_the_middle_does_not_generate_anything():
    r = re.compile(u'a^b')

    with pytest.raises(NoExamples):
        from_regex(r).filter(r.match).example()


def test_end():
    strategy = from_regex(u'abc$')

    strategy.filter(lambda s: s == u'abc').example()
    strategy.filter(lambda s: s == u'abc\n').example()


def test_groupref_exists():
    assert_all_examples(
        from_regex(u'^(<)?a(?(1)>)$'),
        lambda s: s in (u'a', u'a\n', u'<a>', u'<a>\n')
    )
    assert_all_examples(
        from_regex(u'^(a)?(?(1)b|c)$'),
        lambda s: s in (u'ab', u'ab\n', u'c', u'c\n')
    )


def test_groupref_not_shared_between_regex():
    # If group references are (incorrectly!) shared between regex, this would
    # fail as the would only be one reference.
    tuples(from_regex('(a)\\1'), from_regex('(b)\\1')).example()


@given(data())
def test_group_ref_is_not_shared_between_identical_regex(data):
    pattern = re.compile(u"(.+)\\1", re.UNICODE)
    x = data.draw(base_regex_strategy(pattern))
    y = data.draw(base_regex_strategy(pattern))
    assume(x != y)
    assert pattern.match(x).end() == len(x)
    assert pattern.match(y).end() == len(y)


def test_positive_lookbehind():
    from_regex(u'.*(?<=ab)c').filter(lambda s: s.endswith(u'abc')).example()


def test_positive_lookahead():
    from_regex(u'a(?=bc).*').filter(lambda s: s.startswith(u'abc')).example()


def test_negative_lookbehind():
    # no efficient support
    strategy = from_regex(u'[abc]*(?<!abc)d')

    assert_all_examples(strategy, lambda s: not s.endswith(u'abcd'))
    with pytest.raises(NoExamples):
        strategy.filter(lambda s: s.endswith(u'abcd')).example()


def test_negative_lookahead():
    # no efficient support
    strategy = from_regex(u'ab(?!cd)[abcd]*')

    assert_all_examples(strategy, lambda s: not s.startswith(u'abcd'))
    with pytest.raises(NoExamples):
        strategy.filter(lambda s: s.startswith(u'abcd')).example()


@pytest.mark.skipif(sys.version_info[:2] < (3, 6),
                    reason='requires Python 3.6')
def test_subpattern_flags():
    strategy = from_regex(u'(?i)a(?-i:b)')

    # "a" is case insensitive
    strategy.filter(lambda s: s[0] == u'a').example()
    strategy.filter(lambda s: s[0] == u'A').example()
    # "b" is case sensitive
    strategy.filter(lambda s: s[1] == u'b').example()

    with pytest.raises(NoExamples):
        strategy.filter(lambda s: s[1] == u'B').example()


@given(text(max_size=100) | binary(max_size=100))
def test_fuzz_stuff(pattern):
    try:
        regex = re.compile(pattern)
    except re.error:
        reject()

    @given(from_regex(regex))
    def inner(ex):
        assert regex.match(ex)

    try:
        inner()
    except (NoExamples, FailedHealthCheck):
        reject()


@pytest.mark.parametrize('pattern', [b'.', u'.'])
def test_regex_have_same_type_as_pattern(pattern):
    @given(from_regex(pattern))
    def test_result_type(s):
        assert type(s) == type(pattern)

    test_result_type()
