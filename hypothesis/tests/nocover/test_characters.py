# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import codecs
import string
from encodings.aliases import aliases

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.internal.charmap import intervals_from_codec
from hypothesis.strategies._internal.lazy import unwrap_strategies

from tests.common.debug import find_any
from tests.common.utils import Why, xfail_on_crosshair

IDENTIFIER_CHARS = string.ascii_letters + string.digits + "_"


@given(st.characters(exclude_characters=IDENTIFIER_CHARS))
def test_large_blacklist(c):
    assert c not in IDENTIFIER_CHARS


@xfail_on_crosshair(Why.symbolic_outside_context)  # seems like a crosshair bug here
@given(st.data())
def test_arbitrary_blacklist(data):
    blacklist = data.draw(st.text(st.characters(max_codepoint=1000), min_size=1))
    ords = list(map(ord, blacklist))
    c = data.draw(
        st.characters(
            exclude_characters=blacklist,
            min_codepoint=max(0, min(ords) - 1),
            max_codepoint=max(0, max(ords) + 1),
        )
    )
    assert c not in blacklist


def _enc(cdc):
    try:
        "".encode(cdc)
        return True
    except Exception:
        return False


lots_of_encodings = sorted(x for x in set(aliases).union(aliases.values()) if _enc(x))
assert len(lots_of_encodings) > 100  # sanity-check


def non_roundtrip_chars(codec):
    return "".join(map(chr, intervals_from_codec(codecs.lookup(codec).name)[1]))


@pytest.mark.skipif(
    settings.get_current_profile_name() == "crosshair",
    reason="takes 2000s; large & slow symbolic strings",
)
@given(data=st.data(), codec=st.sampled_from(lots_of_encodings))
@settings(max_examples=5)
def test_can_constrain_characters_to_codec(data, codec):
    strategy = st.characters(codec=codec)
    try:
        strategy.validate()
    except InvalidArgument as err:
        # codecs with non-round-tripping characters require an explicit decision
        assert "round-trip" in str(err)
        strategy = st.characters(
            codec=codec, exclude_characters=non_roundtrip_chars(codec)
        )
    s = data.draw(st.text(strategy, min_size=25))
    assert s.encode(codec).decode(codec) == s


@pytest.mark.parametrize(
    "codec, chars",
    [
        ("shift_jis", "¥‾"),  # they encode to the same bytes as backslash and tilde
        ("iso2022_jp", "\x1b"),  # the escape character of this stateful codec
    ],
)
def test_non_round_tripping_characters_must_be_decided(codec, chars):
    assert non_roundtrip_chars(codec) == chars
    with pytest.raises(InvalidArgument, match="round-trip"):
        st.characters(codec=codec).validate()
    # deciding only some of them is not enough
    if len(chars) > 1:
        with pytest.raises(InvalidArgument, match="round-trip"):
            st.characters(codec=codec, include_characters=chars[0]).validate()
    # excluding them all works, and generates none of them
    excluded = unwrap_strategies(st.characters(codec=codec, exclude_characters=chars))
    assert not any(ord(c) in excluded.intervals for c in chars)
    # including them all works too, and they can then be generated
    included = unwrap_strategies(st.characters(codec=codec, include_characters=chars))
    assert all(ord(c) in included.intervals for c in chars)
    # as does a mixed decision
    mixed = unwrap_strategies(
        st.characters(
            codec=codec, include_characters=chars[0], exclude_characters=chars[1:]
        )
    )
    assert ord(chars[0]) in mixed.intervals
    assert not any(ord(c) in mixed.intervals for c in chars[1:])


def test_no_error_if_other_arguments_exclude_non_round_tripping_characters():
    # "¥" (U+A5) and "‾" (U+203E) are already outside the codepoint range
    strategy = st.characters(codec="shift_jis", min_codepoint=200, max_codepoint=8000)
    strategy.validate()
    find_any(strategy)


@pytest.mark.skipif(
    settings.get_current_profile_name() == "crosshair",
    reason="large & slow symbolic strings",
)
@pytest.mark.parametrize("codec", ["shift_jis", "cp950", "iso2022_jp", "iso2022_kr"])
@given(data=st.data())
def test_codec_strings_round_trip_if_non_round_tripping_chars_excluded(codec, data):
    chars = st.characters(codec=codec, exclude_characters=non_roundtrip_chars(codec))
    s = data.draw(st.text(chars, min_size=1))
    assert s.encode(codec).decode(codec) == s
