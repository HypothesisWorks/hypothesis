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

import string

from hypothesis import given, strategies as st

IDENTIFIER_CHARS = string.ascii_letters + string.digits + "_"


@given(st.characters(blacklist_characters=IDENTIFIER_CHARS))
def test_large_blacklist(c):
    assert c not in IDENTIFIER_CHARS


@given(st.data())
def test_arbitrary_blacklist(data):
    blacklist = data.draw(st.text(st.characters(max_codepoint=1000), min_size=1))
    ords = list(map(ord, blacklist))
    c = data.draw(
        st.characters(
            blacklist_characters=blacklist,
            min_codepoint=max(0, min(ords) - 1),
            max_codepoint=max(0, max(ords) + 1),
        )
    )
    assert c not in blacklist
