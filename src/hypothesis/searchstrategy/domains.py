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
from hypothesis.searchstrategy.strategies import MappedSearchStrategy

class DomainStrategy(MappedSearchStrategy):

    """A strategy for domain name strings, defined in terms of lists of text
    strings."""


    def __init__(self, alphabet, unsafe, min_subdomains, max_subdomains):
        super(DomainStrategy, self).__init__(
            strategy=fixed_dictionaries({
                'labels': lists(
                    # Behöver generera denna on-the-fly för att inte slå i alla begränsningar.
                    # Typ en label i taget, koll längd, generera en till osv.
                    # Lättast baklänges, top domän, subdomän, subdoän, ...
                    # Dessutom behöver jag idna alla strängar, och så vidare.
                    alphabet.filter(lambda label: "." not in label),
                    min_value=min_subdomains, max_value=max_subdomains
                ),
                'top-level': st.one_of(SUFFIX_LIST if unsafe else SAFE_DOMAINS)
            })
        )

    @staticmethod
    def canonicalize(string):
        return idna.ToASCII(idna.nameprep(to_unicode(string)))

    def pack(self, labels, top_level):
        return "%s.%s" % (
            u'.'.join(value['labels']), value['top-level']
        )

    # Probably use do_draw to ensure min/max bounds better.
    # Each label must be 1 < 63 octets/bytes long,
    # the number of labels must be 0 < 127 and
    # the total length must be < 253


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
