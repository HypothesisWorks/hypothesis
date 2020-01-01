# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import re
import string
from functools import reduce

import hypothesis.strategies as st
from hypothesis import assume, given, reject
from hypothesis.strategies._internal.regex import base_regex_strategy


@st.composite
def charset(draw):
    negated = draw(st.booleans())
    chars = draw(st.text(string.ascii_letters + string.digits, min_size=1))
    if negated:
        return "[^%s]" % (chars,)
    else:
        return "[%s]" % (chars,)


COMBINED_MATCHER = re.compile("[?+*]{2}")


@st.composite
def conservative_regex(draw):
    result = draw(
        st.one_of(
            st.just("."),
            st.sampled_from([re.escape(c) for c in string.printable]),
            charset(),
            CONSERVATIVE_REGEX.map(lambda s: "(%s)" % (s,)),
            CONSERVATIVE_REGEX.map(lambda s: s + "+"),
            CONSERVATIVE_REGEX.map(lambda s: s + "?"),
            CONSERVATIVE_REGEX.map(lambda s: s + "*"),
            st.lists(CONSERVATIVE_REGEX, min_size=1, max_size=3).map("|".join),
            st.lists(CONSERVATIVE_REGEX, min_size=1, max_size=3).map("".join),
        )
    )
    assume(COMBINED_MATCHER.search(result) is None)
    control = sum(result.count(c) for c in "?+*")
    assume(control <= 3)
    return result


CONSERVATIVE_REGEX = conservative_regex()
FLAGS = st.sets(st.sampled_from([getattr(re, "A", 0), re.I, re.M, re.S])).map(
    lambda flag_set: reduce(int.__or__, flag_set, 0)
)


@given(st.data())
def test_conservative_regex_are_correct_by_construction(data):
    pattern = re.compile(data.draw(CONSERVATIVE_REGEX), flags=data.draw(FLAGS))
    result = data.draw(base_regex_strategy(pattern))
    assert pattern.search(result) is not None


@given(st.data())
def test_fuzz_stuff(data):
    pattern = data.draw(
        st.text(min_size=1, max_size=5)
        | st.binary(min_size=1, max_size=5)
        | CONSERVATIVE_REGEX.filter(bool)
    )
    flags = data.draw(FLAGS)

    try:
        regex = re.compile(pattern, flags=flags)
    except (re.error, FutureWarning):
        # Possible nested sets, e.g. "[[", trigger a FutureWarning
        reject()

    ex = data.draw(st.from_regex(regex))
    assert regex.search(ex)
