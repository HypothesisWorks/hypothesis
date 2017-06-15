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

pytest_plugins = str('pytester')


PYTEST_TESTSUITE = """
from hypothesis import given
from hypothesis.strategies import integers
import pytest

@given(xs=integers())
def test_to_be_skipped(xs):
    if xs == 0:
        pytest.skip()
    else:
        assert xs == 0
"""


def test_no_falsifying_example_if_pytest_skip(testdir):
    """If ``pytest.skip() is called during a test, Hypothesis should not
    continue running the test and shrink process, nor should it print
    anything about falsifying examples."""
    script = testdir.makepyfile(PYTEST_TESTSUITE)
    result = testdir.runpytest(script, '--verbose', '--strict', '-m',
                               'hypothesis')
    out = '\n'.join(result.stdout.lines)
    assert 'Falsifying example' not in out
