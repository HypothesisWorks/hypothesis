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

from hypothesis.internal.compat import PY2, WINDOWS, hunichr, \
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

def test_emits_unicode():
    @settings(verbosity=Verbosity.verbose)
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


TRACEBACKHIDE_TIMEOUT = """
from hypothesis import given, settings
from hypothesis.strategies import integers
from hypothesis.errors import HypothesisDeprecationWarning

import time
import warnings
import pytest


def test_timeout_traceback_is_hidden():
    with warnings.catch_warnings(record=True):
        warnings.simplefilter('ignore', HypothesisDeprecationWarning)
        @given(integers())
        @settings(timeout=1)
        def inner(i):
            time.sleep(1.1)
        inner()
"""


def get_line_num(token, result, skip_n=0):
    for i, line in enumerate(result.stdout.lines):
        if token in line:
            if skip_n == 0:
                return i
            else:
                skip_n -= 1
    assert False, \
        'Token %r not found (after skipping %r appearances)' % (token, skip_n)


def test_timeout_traceback_is_hidden(testdir):
    script = testdir.makepyfile(TRACEBACKHIDE_TIMEOUT)
    result = testdir.runpytest(script, '--verbose')
    # `def inner` shows up in the output twice: once when pytest shows us the
    # source code of the failing test, and once in the traceback.
    # It's the 2nd that should be next to the "Timeout: ..." message.
    def_line = get_line_num('def inner', result, skip_n=1)
    timeout_line = get_line_num('Timeout: Ran out of time', result)
    # If __tracebackhide__ works, then the Timeout error message will be
    # next to the test name.  If it doesn't work, then the message will be
    # many lines apart with source code dump between them.
    assert timeout_line - def_line == 1


TRACEBACKHIDE_HEALTHCHECK = """
from hypothesis import given, settings
from hypothesis.strategies import integers
import time
@given(integers().map(lambda x: time.sleep(0.2)))
def test_healthcheck_traceback_is_hidden(x):
    pass
"""


def test_healthcheck_traceback_is_hidden(testdir):
    script = testdir.makepyfile(TRACEBACKHIDE_HEALTHCHECK)
    result = testdir.runpytest(script, '--verbose')
    def_token = '__ test_healthcheck_traceback_is_hidden __'
    timeout_token = ': FailedHealthCheck'
    def_line = get_line_num(def_token, result)
    timeout_line = get_line_num(timeout_token, result)
    assert timeout_line - def_line == 6
