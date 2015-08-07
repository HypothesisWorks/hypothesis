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

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest

pytest_plugins = str('pytester')

TESTSUITE = """
from hypothesis import given, Settings, Verbosity

@given(int, settings=Settings(verbosity=Verbosity.verbose))
def test_should_be_verbose(x):
    pass
"""


@pytest.mark.parametrize('capture,expected', [
    ('no', True),
    ('fd', False),
])
def test_output_without_capture(testdir, capture, expected):
    script = testdir.makepyfile(TESTSUITE)
    result = testdir.runpytest(script, '--verbose', '--capture', capture)
    out = '\n'.join(result.stdout.lines)
    assert 'test_should_be_verbose' in out
    assert ('Trying example' in out) == expected
    assert result.ret == 0
