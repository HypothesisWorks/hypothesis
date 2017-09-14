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

import hypothesis.strategies as st
from hypothesis import given, settings
from tests.common.utils import all_values
from hypothesis.database import InMemoryExampleDatabase


def test_tracks_and_saves_coverage():
    db = InMemoryExampleDatabase()

    def do_nothing(): pass

    @settings(database=db)
    @given(st.integers())
    def test_branching(i):
        if i < 0:
            do_nothing()
        if i == 0:
            do_nothing()
        if i > 0:
            do_nothing()

    test_branching()

    assert len(all_values(db)) == 3
