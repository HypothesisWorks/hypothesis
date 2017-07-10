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

"""This module contains various provisional APIs and strategies.

It is intended for internal use, to ease code reuse, and is not stable.
Point releases may move or break the contents at any time!

"""

from __future__ import division, print_function, absolute_import

import string

import hypothesis.strategies as st


@st.defines_strategy
def emails():
    """A temporary emails strategy, for the Django extra module.

    See https://github.com/HypothesisWorks/hypothesis-python/issues/162
    for work on a permanent replacement.

    """
    atoms = st.text(string.ascii_letters + string.digits + '_-', min_size=1)
    domains = st.builds(
        lambda x, y: '.'.join(x + [y]),
        st.lists(atoms, min_size=1),
        st.sampled_from(['com', 'net', 'org', 'biz', 'info'])
    )
    return st.builds(
        '{}@{}'.format,
        atoms | st.builds('{}+{}'.format, atoms, atoms),
        st.sampled_from(['gmail.com', 'yahoo.com', 'hotmail.com']) | domains
    )


@st.defines_strategy
def IP4_addr_strings():
    """Another temporary strategy for the Django extra module."""
    return st.builds('{}.{}.{}.{}'.format, *(4 * [st.integers(0, 255)]))


@st.defines_strategy
def IP6_addr_strings():
    """Yet another temporary strategy for the Django extra module."""
    part = st.integers(0, 2**16 - 1).map(u'{:04x}'.format)
    return st.tuples(*[part] * 8).map(lambda a: u':'.join(a).upper())
