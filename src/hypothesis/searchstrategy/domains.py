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
import inspect
from pathlib import Path
from encodings import idna

import hypothesis.strategies as st
from hypothesis.internal.compat import to_unicode
from hypothesis.searchstrategy.strategies import SearchStrategy

MAX_LABEL_SIZE = 63
MAX_LABEL_COUNT = 127
MAX_DOMAIN_SIZE = 253

# Each label must be 1 < 63 octets/bytes long,
# the number of labels must be 0 < 127 and
# the total length must be < 253

class DomainStrategy(SearchStrategy):

    """A strategy for domain name strings, defined in terms of lists of text
    strings."""


    def __init__(self, alphabet, unsafe, min_subdomains, max_subdomains):
        SearchStrategy.__init__(self)
        self.alphabet = alphabet
        self.unsafe = unsafe
        self.min_subdomains = min_subdomains
        self.max_subdomains = max_subdomains
        self.subdomain_count = st.integers(
            min_value=self.min_subdomain, max_value=self.max_subdomain
        )

    @staticmethod
    def canonicalize(string):
        return idna.ToASCII(idna.nameprep(to_unicode(string)))

    def do_draw(self, data):
        subdomain_count = data.draw(self.subdomain_count)
        labels = [] # RFC term for subdomains
        total = len(top_level) + 1 # One extra for the dot

        while total < MAX_DOMAIN_SIZE and len(labels) < subdomain_count:
            try:
                label = self.canonicalize(data.draw(st.text(
                    min_size=1, max_size=MAX_LABEL_SIZE, alphabet=self.alphabet
                )))
            except UnicodeError:
                continue

            total += len(label) + 1 # One extra for the dot
            labels.append(label)

        while total > MAX_DOMAIN_SIZE or len(labels) > subdomain_count:
            total -= len(labels.pop())
            total -= 1

        # Append the top domain
        labels.append(data.draw(st.sampled_from(SUFFIX_LIST)))
        domain = ".".join(labels)

        assert len(domain) < MAX_DOMAIN_SIZE
        return domain


suffix_list_path = Path(inspect.getfile(inspect.currentframe()))
suffix_list_path = suffix_list_path / ".." / ".." / ".." / ".." / "public_suffix_list.dat"
suffix_list_path = suffix_list_path.resolve()

SUFFIX_LIST = set((
    # These arabic domain chokes on canonicalization, so just hardcode them.
    # 'ایران.ir'
    # 'ايران.ir'
    "xn--mgba3a4f16a.ir", "xn--mgba3a4fra.ir"

    # This hebrew one for Jerusalem also chokes, but I didn't find the idna
    # encoded version
    # 'ירושלים.museum'
))

_SUFFIX_REGEXP = re.compile(r"^[^!/]\S+")
_STRIP_WILDCARD = re.compile("^[*.]*(.*)$")
with suffix_list_path.open() as suffix_list:
    for line in suffix_list:
        match = _SUFFIX_REGEXP.search(line)
        if match:
            line = _STRIP_WILDCARD.search(match.group(0)).group(0)
            try:
                SUFFIX_LIST.add(DomainStrategy.canonicalize(line))
            except UnicodeError:
                # Ignore unicode errors for the domains mentioned above.
                pass
