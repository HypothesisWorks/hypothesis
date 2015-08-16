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

from __future__ import division, print_function, absolute_import

import pytest
from hypothesis import find, given, reporting
from tests.common.utils import capture_out
from hypothesis.settings import Settings, Verbosity
from hypothesis.reporting import debug_report, verbose_report
from hypothesis.strategies import just, integers


def test_can_suppress_output():
    @given(integers())
    def test_int(x):
        assert False

    with capture_out() as o:
        with reporting.with_reporter(reporting.silent):
            with pytest.raises(AssertionError):
                test_int()
    assert u'Falsifying example' not in o.getvalue()


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
    with Settings(verbosity=Verbosity.verbose):
        with capture_out() as o:
            debug_report(u'Hi')
    assert not o.getvalue()


def test_does_print_debug_in_debug():
    with Settings(verbosity=Verbosity.debug):
        with capture_out() as o:
            debug_report(u'Hi')
    assert u'Hi' in o.getvalue()


def test_does_print_verbose_in_debug():
    with Settings(verbosity=Verbosity.debug):
        with capture_out() as o:
            verbose_report(u'Hi')
    assert u'Hi' in o.getvalue()


def test_prints_debug_on_no_simplification():
    with Settings(verbosity=Verbosity.debug):
        with capture_out() as o:
            find(just(u'hi'), bool)
    v = o.getvalue()
    print(v)
    assert u'No simplifiers' in v
