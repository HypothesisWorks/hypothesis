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
import string

import hypothesis.strategies as st
from hypothesis import given, assume, reject
from hypothesis.errors import NoExamples, FailedHealthCheck
from hypothesis.searchstrategy.regex import base_regex_strategy


@st.composite
def charset(draw):
    negated = draw(st.booleans())
    chars = draw(st.text(string.ascii_letters + string.digits, min_size=1))
    if negated:
        return u"[^%s]" % (chars,)
    else:
        return u"[%s]" % (chars,)


COMBINED_MATCHER = re.compile(u"[?+*]{2}")


@st.composite
def conservative_regex(draw):
    result = draw(st.one_of(
        st.just(u"."),
        charset(),
        CONSERVATIVE_REGEX.map(lambda s: u"(%s)" % (s,)),
        CONSERVATIVE_REGEX.map(lambda s: s + u'+'),
        CONSERVATIVE_REGEX.map(lambda s: s + u'?'),
        CONSERVATIVE_REGEX.map(lambda s: s + u'*'),
        st.lists(CONSERVATIVE_REGEX, min_size=1).map(u"|".join),
        st.lists(CONSERVATIVE_REGEX, min_size=1).map(u"".join),
    ))
    assume(COMBINED_MATCHER.search(result) is None)
    return result


CONSERVATIVE_REGEX = conservative_regex()


@given(st.data())
def test_conservative_regex_are_correct_by_construction(data):
    pattern = re.compile(data.draw(CONSERVATIVE_REGEX))
    pattern = re.compile(pattern)
    result = data.draw(base_regex_strategy(pattern))
    assert pattern.match(result) is not None


@given(st.text(max_size=100) | st.binary(max_size=100) | CONSERVATIVE_REGEX)
def test_fuzz_stuff(pattern):
    try:
        regex = re.compile(pattern)
    except re.error:
        reject()

    @given(st.from_regex(regex))
    def inner(ex):
        assert regex.match(ex)

    try:
        inner()
    except (NoExamples, FailedHealthCheck):
        reject()
