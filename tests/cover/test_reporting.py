# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
from hypothesis import given, reporting
from tests.common.utils import capture_out
from hypothesis.settings import Settings, Verbosity
from hypothesis.reporting import debug_report, verbose_report


def test_can_suppress_output():
    @given(integers())
    def test_int(x):
        assert False

    with capture_out() as o:
        with reporting.with_reporter(reporting.silent):
            with pytest.raises(AssertionError):
                test_int()
    assert 'Falsifying example' not in o.getvalue()


def test_prints_output_by_default():
    @given(integers())
    def test_int(x):
        assert False

    with capture_out() as o:
        with reporting.with_reporter(reporting.default):
            with pytest.raises(AssertionError):
                test_int()
    assert 'Falsifying example' in o.getvalue()


def test_does_not_print_debug_in_verbose():
    with Settings(verbosity=Verbosity.verbose):
        with capture_out() as o:
            debug_report('Hi')
    assert not o.getvalue()


def test_does_print_debug_in_debug():
    with Settings(verbosity=Verbosity.debug):
        with capture_out() as o:
            debug_report('Hi')
    assert 'Hi' in o.getvalue()


def test_does_print_verbose_in_debug():
    with Settings(verbosity=Verbosity.debug):
        with capture_out() as o:
            verbose_report('Hi')
    assert 'Hi' in o.getvalue()
