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

import pytest
from coverage import Coverage

import hypothesis.strategies as st
from hypothesis import given, settings
from hypothesis._core import escalate_warning
from tests.common.utils import all_values
from hypothesis.database import InMemoryExampleDatabase
from hypothesis._internal.compat import hrange

pytestmark = pytest.mark.skipif(
    not settings.default.use_coverage,
    reason='Coverage is disabled for this build.'
)


def test_tracks_and_saves_coverage():
    db = InMemoryExampleDatabase()

    def do_nothing():
        """Use in place of pass for empty branches, which don't show up under
        coverge."""
        pass

    @settings(database=db)
    @given(st.integers())
    def test_branching(i):
        if i < -1000:
            do_nothing()
        elif i > 1000:
            do_nothing()
        else:
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


@pytest.mark.parametrize('branch', [False, True])
@pytest.mark.parametrize('timid', [False, True])
def test_achieves_full_coverage(tmpdir, branch, timid):
    @given(st.booleans(), st.booleans(), st.booleans())
    def test(a, b, c):
        some_function_to_test(a, b, c)

    cov = Coverage(
        config_file=False, data_file=str(tmpdir.join('.coverage')),
        branch=branch, timid=timid,
    )
    cov._warn = escalate_warning
    cov.start()
    test()
    cov.stop()

    data = cov.get_data()
    lines = data.lines(__file__)
    for i in hrange(LINE_START + 1, LINE_END + 1):
        assert i in lines


def rnd():
    import random
    return random.gauss(0, 1)


@pytest.mark.parametrize('branch', [False, True])
@pytest.mark.parametrize('timid', [False, True])
def test_does_not_trace_files_outside_inclusion(tmpdir, branch, timid):
    @given(st.booleans())
    def test(a):
        rnd()

    cov = Coverage(
        config_file=False, data_file=str(tmpdir.join('.coverage')),
        branch=branch, timid=timid, include=[__file__],
    )
    cov._warn = escalate_warning
    cov.start()
    test()
    cov.stop()

    data = cov.get_data()
    assert len(list(data.measured_files())) == 1
