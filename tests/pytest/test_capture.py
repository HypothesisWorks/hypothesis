# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest

from hypothesis.internal.compat import PY2, hunichr, WINDOWS, \
    escape_unicode_characters

pytest_plugins = str('pytester')

TESTSUITE = """
from hypothesis import given, settings, Verbosity
from hypothesis.strategies import integers

@settings(verbosity=Verbosity.verbose)
@given(integers())
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


UNICODE_EMITTING = """
import pytest
from hypothesis import given, settings, Verbosity
from hypothesis.strategies import text
from hypothesis.internal.compat import PY3
import sys

@settings(verbosity=Verbosity.verbose)
def test_emits_unicode():
    @given(text())
    def test_should_emit_unicode(t):
        assert all(ord(c) <= 1000 for c in t)
    with pytest.raises(AssertionError):
        test_should_emit_unicode()
"""


@pytest.mark.xfail(
    WINDOWS,
    reason=(
        "Encoding issues in running the subprocess, possibly py.test's fault"))
@pytest.mark.skipif(
    PY2, reason="Output streams don't have encodings in python 2")
def test_output_emitting_unicode(testdir, monkeypatch):
    monkeypatch.setenv('LC_ALL', 'C')
    monkeypatch.setenv('LANG', 'C')
    script = testdir.makepyfile(UNICODE_EMITTING)
    result = getattr(
        testdir, 'runpytest_subprocess', testdir.runpytest)(
        script, '--verbose', '--capture=no')
    out = '\n'.join(result.stdout.lines)
    assert 'test_emits_unicode' in out
    assert escape_unicode_characters(hunichr(1001)) in out
    assert result.ret == 0
