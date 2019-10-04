# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import re
import sys
import unicodedata

import pytest

import hypothesis.strategies as st
from hypothesis import assume, given, settings
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import PY3, PYPY, hrange, hunichr
from hypothesis.searchstrategy.regex import (
    SPACE_CHARS,
    UNICODE_DIGIT_CATEGORIES,
    UNICODE_SPACE_CATEGORIES,
    UNICODE_SPACE_CHARS,
    UNICODE_WEIRD_NONWORD_CHARS,
    UNICODE_WORD_CATEGORIES,
    base_regex_strategy,
)
from tests.common.debug import assert_all_examples, assert_no_examples, find_any


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


def is_digit(s):
    return all(unicodedata.category(c) in UNICODE_DIGIT_CATEGORIES for c in s)


def is_space(s):
    return all(c in SPACE_CHARS for c in s)


def is_unicode_space(s):
    return all(
        unicodedata.category(c) in UNICODE_SPACE_CATEGORIES or c in UNICODE_SPACE_CHARS
        for c in s
    )


def is_word(s):
    return all(
        c == "_"
        or (
            (PY3 or c not in UNICODE_WEIRD_NONWORD_CHARS)
            and unicodedata.category(c) in UNICODE_WORD_CATEGORIES
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

    codepoints = hrange(0, sys.maxunicode + 1) if is_unicode else hrange(1, 128)
    for c in [hunichr(x) for x in codepoints]:
        if isvalidchar(c):
            assert r.search(c), (
                '"%s" supposed to match "%s" (%r, category "%s"), '
                "but it doesn't" % (pattern, c, c, unicodedata.category(c))
            )
        else:
            assert not r.search(c), (
                '"%s" supposed not to match "%s" (%r, category "%s"), '
                "but it does" % (pattern, c, c, unicodedata.category(c))
            )


@pytest.mark.parametrize(
    "category,predicate", [(r"\w", is_word), (r"\d", is_digit), (r"\s", None)]
)
@pytest.mark.parametrize("invert", [False, True])
@pytest.mark.parametrize("is_unicode", [False, True])
def test_matching(category, predicate, invert, is_unicode):
    if predicate is None:
        # Special behaviour due to \x1c, INFORMATION SEPARATOR FOUR
        predicate = is_unicode_space if is_unicode else is_space
    if invert:
        category = category.swapcase()

        def pred(s):
            return not predicate(s)

    else:
        pred = predicate

    _test_matching_pattern(category, pred, is_unicode)


@pytest.mark.parametrize(
    "pattern",
    [
        u".",  # anything
        u"a",
        u"abc",
        u"[a][b][c]",
        u"[^a][^b][^c]",  # literals
        u"[a-z0-9_]",
        u"[^a-z0-9_]",  # range and negative range
        u"ab?",
        u"ab*",
        u"ab+",  # quantifiers
        u"ab{5}",
        u"ab{5,10}",
        u"ab{,10}",
        u"ab{5,}",  # repeaters
        u"ab|cd|ef",  # branch
        u"(foo)+",
        u"(['\"])[a-z]+\\1",
        u"(?:[a-z])(['\"])[a-z]+\\1",
        u"(?P<foo>['\"])[a-z]+(?P=foo)",  # groups
        u"^abc",  # beginning
        u"\\d",
        u"[\\d]",
        u"[^\\D]",
        u"\\w",
        u"[\\w]",
        u"[^\\W]",
        u"\\s",
        u"[\\s]",
        u"[^\\S]",  # categories
    ],
)
@pytest.mark.parametrize("encode", [False, True])
def test_can_generate(pattern, encode):
    if encode:
        pattern = pattern.encode("ascii")
    assert_all_examples(st.from_regex(pattern), re.compile(pattern).search)


@pytest.mark.parametrize(
    "pattern",
    [
        re.compile(u"\\Aa\\Z", re.IGNORECASE),
        u"(?i)\\Aa\\Z",
        re.compile(u"\\A[ab]\\Z", re.IGNORECASE),
        u"(?i)\\A[ab]\\Z",
    ],
)
def test_literals_with_ignorecase(pattern):
    strategy = st.from_regex(pattern)

    find_any(strategy, lambda s: s == u"a")
    find_any(strategy, lambda s: s == u"A")


@pytest.mark.parametrize(
    "pattern", [re.compile(u"\\A[^a][^b]\\Z", re.IGNORECASE), u"(?i)\\A[^a][^b]\\Z"]
)
def test_not_literal_with_ignorecase(pattern):
    assert_all_examples(
        st.from_regex(pattern),
        lambda s: s[0] not in (u"a", u"A") and s[1] not in (u"b", u"B"),
    )


def test_any_doesnt_generate_newline():
    assert_all_examples(st.from_regex(u"\\A.\\Z"), lambda s: s != u"\n")


@pytest.mark.parametrize("pattern", [re.compile(u"\\A.\\Z", re.DOTALL), u"(?s)\\A.\\Z"])
def test_any_with_dotall_generate_newline(pattern):
    find_any(
        st.from_regex(pattern), lambda s: s == u"\n", settings(max_examples=10 ** 6)
    )


@pytest.mark.parametrize("pattern", [re.compile(b"\\A.\\Z", re.DOTALL), b"(?s)\\A.\\Z"])
def test_any_with_dotall_generate_newline_binary(pattern):
    find_any(
        st.from_regex(pattern), lambda s: s == b"\n", settings(max_examples=10 ** 6)
    )


@pytest.mark.parametrize(
    "pattern",
    [
        u"\\d",
        u"[\\d]",
        u"[^\\D]",
        u"\\w",
        u"[\\w]",
        u"[^\\W]",
        u"\\s",
        u"[\\s]",
        u"[^\\S]",
    ],
)
@pytest.mark.parametrize("is_unicode", [False, True])
@pytest.mark.parametrize("invert", [False, True])
def test_groups(pattern, is_unicode, invert):
    if u"d" in pattern.lower():
        group_pred = is_digit
    elif u"w" in pattern.lower():
        group_pred = is_word
    else:
        # Special behaviour due to \x1c, INFORMATION SEPARATOR FOUR
        group_pred = is_unicode_space if is_unicode else is_space

    if invert:
        pattern = pattern.swapcase()
        _p = group_pred

        def group_pred(s):  # pylint:disable=function-redefined
            return not _p(s)

    pattern = u"^%s\\Z" % (pattern,)

    compiler = unicode_regex if is_unicode else ascii_regex
    strategy = st.from_regex(compiler(pattern))

    find_any(strategy.filter(group_pred), is_ascii)
    if is_unicode:
        find_any(strategy, lambda s: group_pred(s) and not is_ascii(s))

    assert_all_examples(strategy, group_pred)


def test_caret_in_the_middle_does_not_generate_anything():
    r = re.compile(u"a^b")

    assert_no_examples(st.from_regex(r))


def test_end_with_terminator_does_not_pad():
    assert_all_examples(st.from_regex(u"abc\\Z"), lambda x: x[-3:] == u"abc")


def test_end():
    strategy = st.from_regex(u"\\Aabc$")

    find_any(strategy, lambda s: s == u"abc")
    find_any(strategy, lambda s: s == u"abc\n")


def test_groupref_exists():
    assert_all_examples(
        st.from_regex(u"^(<)?a(?(1)>)$"),
        lambda s: s in (u"a", u"a\n", u"<a>", u"<a>\n"),
    )
    assert_all_examples(
        st.from_regex(u"^(a)?(?(1)b|c)$"), lambda s: s in (u"ab", u"ab\n", u"c", u"c\n")
    )


def test_impossible_negative_lookahead():
    assert_no_examples(st.from_regex(u"(?!foo)foo"))


@given(st.from_regex(u"(\\Afoo\\Z)"))
def test_can_handle_boundaries_nested(s):
    assert s == u"foo"


def test_groupref_not_shared_between_regex():
    # If group references are (incorrectly!) shared between regex, this would
    # fail as the would only be one reference.
    st.tuples(st.from_regex("(a)\\1"), st.from_regex("(b)\\1")).example()


@pytest.mark.skipif(
    PYPY and sys.version_info[:2] == (3, 6),  # Skip for now so we can test the rest
    reason=r"Under PyPy3.6, the pattern generates but does not match \x80\x80",
)
@given(st.data())
def test_group_ref_is_not_shared_between_identical_regex(data):
    pattern = re.compile(u"^(.+)\\1\\Z", re.UNICODE)
    x = data.draw(base_regex_strategy(pattern))
    y = data.draw(base_regex_strategy(pattern))
    assume(x != y)
    assert pattern.match(x).end() == len(x)
    assert pattern.match(y).end() == len(y)


@given(st.data())
def test_does_not_leak_groups(data):
    a = data.draw(base_regex_strategy(re.compile(u"^(a)\\Z")))
    assert a == "a"
    b = data.draw(base_regex_strategy(re.compile(u"^(?(1)a|b)(.)\\Z")))
    assert b[0] == "b"


def test_positive_lookbehind():
    find_any(st.from_regex(u".*(?<=ab)c"), lambda s: s.endswith(u"abc"))


def test_positive_lookahead():
    st.from_regex(u"a(?=bc).*").filter(lambda s: s.startswith(u"abc")).example()


def test_negative_lookbehind():
    # no efficient support
    strategy = st.from_regex(u"[abc]*(?<!abc)d")

    assert_all_examples(strategy, lambda s: not s.endswith(u"abcd"))
    assert_no_examples(strategy, lambda s: s.endswith(u"abcd"))


def test_negative_lookahead():
    # no efficient support
    strategy = st.from_regex(u"^ab(?!cd)[abcd]*")

    assert_all_examples(strategy, lambda s: not s.startswith(u"abcd"))
    assert_no_examples(strategy, lambda s: s.startswith(u"abcd"))


@given(st.from_regex(u"^a+\\Z"))
def test_generates_only_the_provided_characters_given_boundaries(xs):
    assert set(xs) == {u"a"}


@given(st.from_regex(u"^(.)?\\1\\Z"))
def test_group_backref_may_not_be_present(s):
    assert len(s) == 2
    assert s[0] == s[1]


@pytest.mark.skipif(sys.version_info[:2] < (3, 6), reason="requires Python 3.6")
def test_subpattern_flags():
    strategy = st.from_regex(u"(?i)\\Aa(?-i:b)\\Z")

    # "a" is case insensitive
    find_any(strategy, lambda s: s[0] == u"a")
    find_any(strategy, lambda s: s[0] == u"A")
    # "b" is case sensitive
    find_any(strategy, lambda s: s[1] == u"b")

    assert_no_examples(strategy, lambda s: s[1] == u"B")


def test_can_handle_binary_regex_which_is_not_ascii():
    bad = b"\xad"
    assert_all_examples(st.from_regex(bad), lambda x: bad in x)


@pytest.mark.parametrize("pattern", [b".", u"."])
def test_regex_have_same_type_as_pattern(pattern):
    @given(st.from_regex(pattern))
    def test_result_type(s):
        assert type(s) == type(pattern)

    test_result_type()


def test_can_pad_strings_arbitrarily():
    find_any(st.from_regex(u"a"), lambda x: x[0] != u"a")
    find_any(st.from_regex(u"a"), lambda x: x[-1] != u"a")


def test_can_pad_empty_strings():
    find_any(st.from_regex(u""), bool)
    find_any(st.from_regex(b""), bool)


def test_can_pad_strings_with_newlines():
    find_any(st.from_regex(u"^$"), bool)
    find_any(st.from_regex(b"^$"), bool)


def test_given_multiline_regex_can_insert_after_dollar():
    find_any(
        st.from_regex(re.compile(u"\\Ahi$", re.MULTILINE)),
        lambda x: "\n" in x and x.split(u"\n")[1],
    )


def test_given_multiline_regex_can_insert_before_caret():
    find_any(
        st.from_regex(re.compile(u"^hi\\Z", re.MULTILINE)),
        lambda x: "\n" in x and x.split(u"\n")[0],
    )


def test_does_not_left_pad_beginning_of_string_marker():
    assert_all_examples(st.from_regex(u"\\Afoo"), lambda x: x.startswith(u"foo"))


def test_bare_caret_can_produce():
    find_any(st.from_regex(u"^"), bool)


def test_bare_dollar_can_produce():
    find_any(st.from_regex(u"$"), bool)


def test_shared_union():
    # This gets parsed as [(ANY, None), (BRANCH, (None, [[], []]))], the
    # interesting feature of which is that it contains empty sub-expressions
    # in the branch.
    find_any(st.from_regex(".|."))


@given(st.data())
def test_issue_992_regression(data):
    strat = st.from_regex(
        re.compile(
            r"""\d +  # the integral part
            \.    # the decimal point
            \d *  # some fractional digits""",
            re.VERBOSE,
        )
    )
    data.draw(strat)


@pytest.mark.parametrize(
    "pattern,matching_str",
    [
        (u"a", u"a"),
        (u"[Aa]", u"A"),
        (u"[ab]*", u"abb"),
        (b"[Aa]", b"A"),
        (b"[ab]*", b"abb"),
        (re.compile(u"[ab]*", re.IGNORECASE), u"aBb"),
        (re.compile(b"[ab]", re.IGNORECASE), b"A"),
    ],
)
def test_fullmatch_generates_example(pattern, matching_str):
    find_any(
        st.from_regex(pattern, fullmatch=True),
        lambda s: s == matching_str,
        settings(max_examples=10 ** 6),
    )


@pytest.mark.parametrize(
    "pattern,eqiv_pattern",
    [
        (u"a", u"\\Aa\\Z"),
        (u"[Aa]", u"\\A[Aa]\\Z"),
        (u"[ab]*", u"\\A[ab]*\\Z"),
        (b"[Aa]", br"\A[Aa]\Z"),
        (b"[ab]*", br"\A[ab]*\Z"),
        (
            re.compile(u"[ab]*", re.IGNORECASE),
            re.compile(u"\\A[ab]*\\Z", re.IGNORECASE),
        ),
        (re.compile(br"[ab]", re.IGNORECASE), re.compile(br"\A[ab]\Z", re.IGNORECASE)),
    ],
)
def test_fullmatch_matches(pattern, eqiv_pattern):
    assert_all_examples(
        st.from_regex(pattern, fullmatch=True), lambda s: re.match(eqiv_pattern, s)
    )


def test_fullmatch_must_be_bool():
    with pytest.raises(InvalidArgument):
        st.from_regex("a", fullmatch=None).validate()


def test_issue_1786_regression():
    st.from_regex(re.compile("\\\\", flags=re.IGNORECASE)).validate()
