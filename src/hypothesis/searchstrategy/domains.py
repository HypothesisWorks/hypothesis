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
from encodings import idna

import hypothesis.strategies as st
from hypothesis import assume
from hypothesis.internal.compat import to_unicode
from hypothesis.searchstrategy._domains import raw_data
from hypothesis.searchstrategy.strategies import SearchStrategy

# Each label must be 1 < 63 octets/bytes long,
# the number of labels must be 0 < 127 and
# the total length must be < 253

MAX_LABEL_SIZE = 63
MAX_LABEL_COUNT = 127
MAX_DOMAIN_SIZE = 253


class DomainStrategy(SearchStrategy):

    """A strategy for domain name strings, defined in terms of lists of text
    strings."""

    def __init__(self, alphabet, example_domains_only):
        SearchStrategy.__init__(self)
        self.label_text = st.text(
            min_size=1, max_size=MAX_LABEL_SIZE, alphabet=alphabet
        ).map(DomainStrategy.canonicalize)

        if example_domains_only:
            self.top_level = st.sampled_from(EXAMPLE_DOMAINS)
        else:
            self.top_level = st.sampled_from(SUFFIX_LIST)

    @staticmethod
    def canonicalize(string):
        try:
            return idna.ToASCII(idna.nameprep(to_unicode(string)))
        except UnicodeError:
            assume(False)

    def do_draw(self, data):
        top_level = data.draw(self.top_level)
        total_length = len(top_level) + 1  # One extra for the dot

        labels = []  # RFC term for subdomains
        count = data.draw(
            st.integers(min_value=1, max_value=MAX_LABEL_COUNT)
        ) - top_level.count('.')

        while total_length < MAX_DOMAIN_SIZE and len(labels) < count:
            label = data.draw(self.label_text)
            labels.append(label)
            total_length += len(label) + 1

        while total_length > MAX_DOMAIN_SIZE or len(labels) > count:
            total_length -= len(labels.pop())
            total_length -= 1

        labels.append(top_level)
        domain = '.'.join(labels)

        assume(len(domain) < MAX_DOMAIN_SIZE)
        return domain


EXAMPLE_DOMAINS = ['example', 'example.com', 'example.org']
SUFFIX_LIST = set((
    # These arabic domain chokes on canonicalization, so just hardcode them.
    # 'ایران.ir'
    # 'ايران.ir'
    'xn--mgba3a4f16a.ir', 'xn--mgba3a4fra.ir'

    # This hebrew one for Jerusalem also chokes, but I didn't find the idna
    # encoded version
    # 'ירושלים.museum'
))

_SUFFIX_REGEXP = re.compile(r"^[^!/]\S+")
_STRIP_WILDCARD = re.compile('^[*.]*(.*)$')
for line in raw_data:
    match = _SUFFIX_REGEXP.search(line)
    if match:
        line = _STRIP_WILDCARD.search(match.group(0)).group(0)
        try:
            SUFFIX_LIST.add(DomainStrategy.canonicalize(line))
        except UnicodeError:
            # Ignore unicode errors for the domains mentioned above.
            pass
