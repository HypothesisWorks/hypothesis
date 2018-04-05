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

from __future__ import division, print_function, absolute_import

import hypothesis.strategies as st
from hypothesis import find, settings


def test_max_shrinks():
    seen = set()
    zero = b'\0' * 100

    def tracktrue(s):
        if s == zero:
            return False
        seen.add(s)
        return True

    find(
        st.binary(min_size=100, max_size=100), tracktrue,
        settings=settings(max_shrinks=1, database=None)
    )
    assert len(seen) == 2
