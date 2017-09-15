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
from coverage import Coverage
from hypothesis import given, settings
from tests.common.utils import all_values
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.internal.compat import hrange


def test_tracks_and_saves_coverage():
    db = InMemoryExampleDatabase()

    def do_nothing():
        """Use in place of pass for empty branches, which don't show up under
        coverge."""
        pass

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


def some_function_to_test(a, b, c):
    result = 0
    if a:
        result += 1
    if b:
        result += 1
    if c:
        result += 1
    return result


LINE_START = some_function_to_test.__code__.co_firstlineno
with open(__file__) as i:
    lines = [l.strip() for l in i]
    LINE_END = LINE_START + lines[LINE_START:].index('')


def test_achieves_full_coverage(tmpdir):
    @given(st.booleans(), st.booleans(), st.booleans())
    def test(a, b, c):
        some_function_to_test(a, b, c)

    cov = Coverage(
        config_file=False, data_file=tmpdir.join('.coveragerc')
    )
    cov.start()
    test()
    cov.stop()

    data = cov.get_data()
    lines = data.lines(__file__)
    for i in hrange(LINE_START + 1, LINE_END + 1):
        assert i in lines
