from __future__ import division, print_function, absolute_import

# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

pytest_plugins = str('pytester')


TESTSUITE = """
from hypothesis import given

@given(int)
def test_foo(x):
    pass

def test_bar():
    pass
"""


def test_mark(testdir):
    script = testdir.makepyfile(TESTSUITE)
    result = testdir.runpytest(script, '--verbose', '--strict', '-m',
                               'hypothesis')
    out = '\n'.join(result.stdout.lines)
    assert '1 passed, 1 deselected' in out
