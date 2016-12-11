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

import re

import pytest

from hypothesis import strategies as st
from hypothesis import find, given
from hypothesis.errors import NoExamples, InvalidArgument


@pytest.mark.parametrize('name,pattern', [
    ('empty', ''),
    ('simple', '^abc$'),
    ('simpleRepetition', '^a+bc$'),
    ('moreRepetition', '^a{2,5}b?c+d*$'),
    ('Repetition', '^a{2,5}b?c+d*$'),
    ('ungreedyRepetition', '^a{2,5}?'),
    ('branching', 'a|b'),
    ('branchingGroup', '^(a|b)$'),
    ('moreGroups', 'ab|v'),
    ('ranges', '^[a-f][d-z][0-9][A-Z]$'),
    ('charactersets', '^[abasff][0124][AJDKSHFD]$'),
    ('longNegativeRanges', '^[^a-zA-Z]$'),
    ('notLiteral', '^[^a][^b][^c]$'),
    ('shortNegativeRanges', '^[^a-b][^D-E][^7-8]$'),
    ('negativeSets', '^[^acsG4]$'),
    ('setsWithHyphens', '^[a\-d][-as][bs-]$'),
    ('negativeSetsWithHyphens', '^[^a\-d][^-as][^bs-]$'),
    ('categoryWord', '^\w[^\w]\W$'),
    ('categoryWhitespace', '^\s[^\s]\S$'),
    ('categoryDigits', '^\d[^\d]\D$'),
    ('wordBoundaries', r'\bfoo\b'),
    ('backRef', '(?P<a>[abc]v[2q])(?P=a)'),
    ('noncapturingGroup', '^(?:abc)def$'),
    ('any', '.'),
    ('positiveLookahead', 'A(?=BCD)'),
    ('negativeLookahead', 'AB(?!CD)'),
    #    ("positiveLookbehind","
    #    ("negativeLookbehind","
    ('groupRef', '(a|b) \1')
])
def test_coverage(name, pattern):
    """This test gives coverage for the regex generator."""
    find(st.regex(pattern), lambda x: re.match(pattern, x) is not None)


@pytest.mark.parametrize('name,pattern', [
    ('backslash1', '\\\\'),
    ('backslash2', r"\\"),
    ('literal', r"last"),
    ('lineend', r"foo.$"),
    ('repetition1', r"ab*"),
    ('repetition2', r"ab+"),
    ('repetition3', r"ab?"),
    ('non-greedy1', r"<.*?>"),
    ('repetition4', r"a{6}"),
    ('repetition5', r"a{3,5}"),
    ('non-greedy2', r"a{3,5}?"),
    ('escape1', r"\*"),
    ('escape2', r"\?"),
    ('set1', r"[amk]"),
    ('set2', r"[a-z]"),
    ('set3', r"[0-5][0-9]"),
    ('set4', r"[0-9A-Fa-f]"),
    ('escape3', r"[a\-z]"),
    ('nonrange', r"[a-]"),
    ('specialset', r"[(+*)]"),
    ('class1', r"[\w]"),
    ('class2', r"[\s]"),
    ('complement1', r"[^5]"),
    ('complement2', r"[^^]"),
    ('parenthesis1', r"[()[\]{}]"),
    ('parenthesis2', r"[]()[{}]"),
    ('branch1', r"A|B"),
    ('backref', r"""(?P<quote>['"]).*?(?P=quote)"""),
    ('positiveLookahead', r"Isaac (?=Asimov)"),
    ('negativeLookahead', r"Isaac (?!Asimov)"),
    #    ("positiveLookbehind", r"(?<=abc)def"),
    #    ("positiveLookbehind2", r"'(?<=-)\w+'"),
    #    ("groupExistance", r"(<)?(\w+@\w+(?:\.\w+)+)(?(1)>)"),
    ('groupRef', '(.+) \1'),
    ('wordBeginning', r'\bfoo\b'),
    #    ("notWordBeginning", r"py\B"),
    ('pythonFunction', r'def\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*\(\s*\):'),
    ('twoWords', r"(\w+) (\w+)"),
    ('fullName', r"(?P<first_name>\w+) (?P<last_name>\w+)"),
    ('float', r"(\d+)\.(\d+)"),
    ('poker', r"^[a2-9tjqk]{5}$"),
    ('pokerPair', r".*(.).*\1"),
    ('scanf1', r"."),
    ('scanf2', r".{5}"),
    ('scanf3', r"[-+]?\d+"),
    ('scanf4', r"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?"),
    ('scanf5', r"[-+]?(0[xX][\dA-Fa-f]+|0[0-7]*|\d+)"),
    ('scanf6', r"[-+]?[0-7]+"),
    ('scanf7', r"\S+"),
    ('scanf8', r"\d+"),
    ('scanf9', r"[-+]?(0[xX])?[\dA-Fa-f]+")
])
def test_re_examples(name, pattern):
    """This test exercises all examples from the python documentation."""
    find(st.regex(pattern), lambda x: re.match(pattern, x) is not None)


# Try to exhaust the set of matching strings for a number of simple res
