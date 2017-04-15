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
