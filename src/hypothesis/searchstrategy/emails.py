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

import string

import hypothesis.strategies as st
from hypothesis import assume
from hypothesis.searchstrategy.strategies import SearchStrategy

MAX_ADDRESS_SIZE = 254
MAX_LOCAL_PART_SIZE = 64
LOCAL_PART_TEXT = st.text(
    alphabet=(
        "!#$%&'*+-/=?^_`{|}~;",
        string.digits,
        string.ascii_letters,
        st.characters(min_codepoint=0x007E)
    ),
    min_size=1,
    max_size=MAX_LOCAL_PART_SIZE
)


class EmailStrategy(SearchStrategy):

    def __init__(self, domains):
        SearchStrategy.__init__(self)
        self.domains = domains

    def do_draw(self, data):
        domain = data.draw(self.domains)
        total_length = len(domain)

        local_parts = []
        count = data.draw(st.integers(
            min_value=1,
            max_value=min(
                # Adjust max size for long domains
                MAX_LOCAL_PART_SIZE, (MAX_ADDRESS_SIZE - len(domain))
            )
        ))

        while total_length < MAX_ADDRESS_SIZE and len(local_parts) < count:
            local_part = data.draw(LOCAL_PART_TEXT)
            local_parts.append(local_part)
            total_length += len(local_parts) + 1

        while total_length > MAX_ADDRESS_SIZE or len(local_parts) > count:
            total_length -= len(local_parts.pop())
            total_length -= 1

        email_address = '.'.join(local_parts) + '@' + domain
        assume(len(email_address) < MAX_ADDRESS_SIZE)
        return email_address
