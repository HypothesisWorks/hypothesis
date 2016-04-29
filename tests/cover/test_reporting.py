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

from __future__ import division, print_function, absolute_import

import os
import sys

import pytest

from hypothesis import given, reporting
from tests.common.utils import capture_out
from hypothesis._settings import settings, Verbosity
from hypothesis.reporting import report, debug_report, verbose_report
from hypothesis.strategies import integers
from hypothesis.internal.compat import PY2


def test_can_suppress_output():
    @given(integers())
    def test_int(x):
        assert False

    with capture_out() as o:
        with reporting.with_reporter(reporting.silent):
            with pytest.raises(AssertionError):
                test_int()
    assert u'Falsifying example' not in o.getvalue()


def test_can_print_bytes():
    with capture_out() as o:
        with reporting.with_reporter(reporting.default):
            report(b'hi')
    assert o.getvalue() == u'hi\n'


def test_prints_output_by_default():
    @given(integers())
    def test_int(x):
        assert False

    with capture_out() as o:
        with reporting.with_reporter(reporting.default):
            with pytest.raises(AssertionError):
                test_int()
    assert u'Falsifying example' in o.getvalue()


def test_does_not_print_debug_in_verbose():
    with settings(verbosity=Verbosity.verbose):
        with capture_out() as o:
            debug_report(u'Hi')
    assert not o.getvalue()


def test_does_print_debug_in_debug():
    with settings(verbosity=Verbosity.debug):
        with capture_out() as o:
            debug_report(u'Hi')
    assert u'Hi' in o.getvalue()


def test_does_print_verbose_in_debug():
    with settings(verbosity=Verbosity.debug):
        with capture_out() as o:
            verbose_report(u'Hi')
    assert u'Hi' in o.getvalue()


@pytest.mark.skipif(
    PY2, reason="Output streams don't have encodings in python 2")
def test_can_report_when_system_locale_is_ascii(monkeypatch):
    import io
    read, write = os.pipe()
    read = io.open(read, 'r', encoding='ascii')
    write = io.open(write, 'w', encoding='ascii')
    monkeypatch.setattr(sys, 'stdout', write)
    reporting.default(u"☃")
