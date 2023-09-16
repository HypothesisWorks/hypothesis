# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import string
from encodings.aliases import aliases

from hypothesis import given, strategies as st

IDENTIFIER_CHARS = string.ascii_letters + string.digits + "_"


@given(st.characters(exclude_characters=IDENTIFIER_CHARS))
def test_large_blacklist(c):
    assert c not in IDENTIFIER_CHARS


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


@given(data=st.data(), codec=st.sampled_from(lots_of_encodings))
def test_can_constrain_characters_to_codec(data, codec):
    s = data.draw(st.text(st.characters(codec=codec), min_size=100))
    s.encode(codec)
