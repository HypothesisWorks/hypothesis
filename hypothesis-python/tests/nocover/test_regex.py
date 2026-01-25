# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re
import string
import sys
from functools import reduce

import pytest

from hypothesis import assume, given, reject, strategies as st
from hypothesis.strategies._internal.regex import (
    IncompatibleWithAlphabet,
    base_regex_strategy,
)


@st.composite
def charset(draw):
    negated = draw(st.booleans())
    chars = draw(st.text(string.ascii_letters + string.digits, min_size=1))
    if negated:
        return f"[^{chars}]"
    else:
        return f"[{chars}]"


COMBINED_MATCHER = re.compile("[?+*]{2}")


@st.composite
def conservative_regex(draw):
    result = draw(
        st.one_of(
            st.just("."),
            st.sampled_from([re.escape(c) for c in string.printable]),
            charset(),
            CONSERVATIVE_REGEX.map(lambda s: f"({s})"),
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
    assume(I_WITH_DOT not in result)  # known to be weird
    return result


CONSERVATIVE_REGEX = conservative_regex()
FLAGS = st.sets(
    st.sampled_from([re.ASCII, re.IGNORECASE, re.MULTILINE, re.DOTALL])
).map(lambda flag_set: reduce(int.__or__, flag_set, 0))


@given(st.data())
def test_conservative_regex_are_correct_by_construction(data):
    pattern = re.compile(data.draw(CONSERVATIVE_REGEX), flags=data.draw(FLAGS))
    result = data.draw(base_regex_strategy(pattern, alphabet=st.characters()))
    # We'll skip "capital I with dot above" due to awful casefolding behaviour
    # and "latin small letter dotless i" for the same reason.
    assume({"ı", "İ"}.isdisjoint(pattern.pattern + result))
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

    try:
        ex = data.draw(st.from_regex(regex))
    except IncompatibleWithAlphabet:
        if isinstance(pattern, str) and flags & re.ASCII:
            with pytest.raises(UnicodeEncodeError):
                pattern.encode("ascii")
            regex = re.compile(pattern, flags=flags ^ re.ASCII)
            ex = data.draw(st.from_regex(regex))
        else:
            raise

    assert regex.search(ex)


@pytest.mark.skipif(sys.version_info[:2] < (3, 11), reason="new syntax")
@given(st.data())
def test_regex_atomic_group(data):
    pattern = "a(?>bc|b)c"
    ex = data.draw(st.from_regex(pattern))
    assert re.search(pattern, ex)


@pytest.mark.skipif(sys.version_info[:2] < (3, 11), reason="new syntax")
@given(st.data())
def test_regex_possessive(data):
    pattern = '"[^"]*+"'
    ex = data.draw(st.from_regex(pattern))
    assert re.search(pattern, ex)


# Some preliminaries, to establish what's happening:
I_WITH_DOT = "\u0130"
assert I_WITH_DOT.swapcase() == "i\u0307"  # note: string of length two!
assert re.compile(I_WITH_DOT, flags=re.IGNORECASE).match(I_WITH_DOT.swapcase())


@given(st.data())
def test_case_insensitive_not_literal_never_constructs_multichar_match(data):
    # So our goal is to confirm that we can never accidentally create a non-matching
    # string by assembling individually allowed characters.
    pattern = re.compile(f"[^{I_WITH_DOT}]+", flags=re.IGNORECASE)
    strategy = st.from_regex(pattern, fullmatch=True)
    for _ in range(5):
        s = data.draw(strategy)
        assert pattern.fullmatch(s) is not None
        # And to be on the safe side, we implement this stronger property:
        assert set(s).isdisjoint(I_WITH_DOT.swapcase())


@given(st.from_regex(re.compile(f"[^{I_WITH_DOT}_]", re.IGNORECASE), fullmatch=True))
def test_no_error_converting_negated_sets_to_strategy(s):
    # CharactersBuilder no longer triggers an internal error converting sets
    # or negated sets to a strategy when multi-char strings are whitelisted.
    pass
