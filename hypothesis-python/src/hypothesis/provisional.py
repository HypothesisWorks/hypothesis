# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

"""This module contains various provisional APIs and strategies.

It is intended for internal use, to ease code reuse, and is not stable.
Point releases may move or break the contents at any time!

Internet strategies should conform to https://tools.ietf.org/html/rfc3696 or
the authoritative definitions it links to.  If not, report the bug!
"""

from __future__ import division, print_function, absolute_import

import string

import hypothesis.strategies as st


@st.defines_strategy_with_reusable_values
def domains():
    """A strategy for :rfc:`1035` fully qualified domain names."""
    atoms = st.text(string.ascii_letters + '0123456789-',
                    min_size=1, max_size=63
                    ).filter(lambda s: '-' not in s[0] + s[-1])
    return st.builds(
        lambda x, y: '.'.join(x + [y]),
        st.lists(atoms, min_size=1),
        # TODO: be more devious about top-level domains
        st.sampled_from(['com', 'net', 'org', 'biz', 'info'])
    ).filter(lambda url: len(url) <= 255)


@st.defines_strategy_with_reusable_values
def ip4_addr_strings():
    """A strategy for IPv4 address strings.

    This consists of four strings representing integers [0..255],
    without zero-padding, joined by dots.
    """
    return st.builds('{}.{}.{}.{}'.format, *(4 * [st.integers(0, 255)]))


@st.defines_strategy_with_reusable_values
def ip6_addr_strings():
    """A strategy for IPv6 address strings.

    This consists of sixteen quads of hex digits (0000 .. FFFF), joined
    by colons.  Values do not currently have zero-segments collapsed.
    """
    part = st.integers(0, 2**16 - 1).map(u'{:04x}'.format)
    return st.tuples(*[part] * 8).map(lambda a: u':'.join(a).upper())
