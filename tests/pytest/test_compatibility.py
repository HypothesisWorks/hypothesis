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

from hypothesis import strategies as st
from hypothesis import given, assume, settings

pytest_plugins = 'pytester'

seen = []


@settings(max_iterations=10, max_examples=10, min_satisfying_examples=1)
@given(st.binary(min_size=10))
def test_mostly_assumes_false(xs):
    if not seen:
        seen.append(xs)
    assume(xs in seen)


def test_basic_failures(testdir):
    script = testdir.makepyfile("""
    from hypothesis import given, settings
    from hypothesis.strategies import integers

    @given(integers())
    def test_yes(i):
        assert True

    @settings(database=None)
    @given(integers())
    def test_no(i):
        assert i < 1001
    """)
    result = testdir.runpytest(script)
    assert result.ret != 0
    assert 'i=1001' in '\n'.join(result.stdout.lines)
