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
from hypothesis import given, note

matches = [
    r'^.$',
    r'.+',
    r'^([1-9]|0[1-9]|[12][0-9]|3[01])\D([1-9]|0[1-9]|1[012])\D(19[0-9][0-9]|20[0-9][0-9])$',
    r'([^<]*)',
    r'^(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5]){3}$',
    r'^(19|20)[\d]{2,2}$',
    r'^-{0,1}\d*\.{0,1}\d+$',
    r'^\d+$',
    r'^([0-9a-zA-Z]([\+\-_\.][0-9a-zA-Z]+)*)+"@(([0-9a-zA-Z][-\w]*[0-9a-zA-Z]*\.)+[a-zA-Z0-9]{2,17})$',
    r'(.*?)\@(.*?)\.(.*?)',
    r'[:alpha:]',
    r'(.*?)',
    r'(.*)',
    r'foo',
    r'\d',
    r'\D',
    r'A{3}',
    r'A{2, 5}',
    r'A{3,12}',
    r'aA{3,12}?a+.b',
    r'\w',
    r'\W',
    r'foo|bar',
    r'(foo|bar)',
    r'[A-F]',
    r'[ABC]',
    r'^foo',
    r'foo$',
    r'[^a]',
    r'[^AEIOU]',
    r'foo(?=bar)',
    r'(foo|bar)baz\1',
    r'a*',
    r'a*?',
    r'(?P<name>foo|bar)baz(?P=name)',
    ]

searches = [
    r'(?<=foo)bar',
    ]

errors = {
    r'(<)?(\w+@\w+(?:\.\w+)+)(?(1)>|$)': "Conditionals not supported",
    }

@pytest.mark.parametrize('pattern', matches)
def test_matches(pattern):
    """Covers simple cases"""
    @given(st.regex(pattern))
    def match(string):
        note("Failure on the following regular expression: %s" % pattern)
        note("The incorrect string produced was: '%s'" % string)
        note("The match object produced was: %s" % re.match(pattern, string))
        assert re.match(pattern, string)

    match()

@pytest.mark.parametrize('pattern', searches)
def test_searches(pattern):
    """Covers cases requiring search"""
    @given(st.regex(pattern))
    def search(string):
        note("Failure on the following regular expression: %s" % pattern)
        note("The incorrect string produced was: '%s'" % string)
        note("The match object produced was: %s" % re.search(pattern, string))
        assert re.search(pattern, string)

    search()

@pytest.mark.parametrize('pattern,error', zip(errors.items))
def test_errors(pattern, error):
    """Covers cases requiring search"""
    try:
        st.regex(pattern)
        raise NotImplementedError("No error for %s" % pattern)
    except Exception as e:
        if not isinstance(e, NotImplementedError):
            raise e
        if not e.args[0] == error:
            raise e

