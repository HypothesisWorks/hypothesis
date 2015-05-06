# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import os

import pytest
import hypothesis.reporting as reporting
from hypothesis import given
from hypothesis.errors import AbnormalExit
from tests.common.utils import capture_out

ForkingTestCase = pytest.importorskip(
    'hypothesis.testrunners.forking'
).ForkingTestCase


def test_runs_normally_if_no_failure():
    class Foo(ForkingTestCase):

        @given({bool})
        def runs_normally(self, x):
            pass

    Foo('runs_normally').runs_normally()


def test_raises_abnormal_exit_if_bad_pickle_in_exception():
    class Boo(Exception):

        def __getstate__(self):
            raise ValueError()

    class TestBoo(ForkingTestCase):

        @given(integers())
        def test_boo(self, x):
            raise Boo()

    with pytest.raises(AbnormalExit):
        TestBoo('test_boo').test_boo()


def test_raises_abnormal_exit_on_premature_child_death():
    class TestForking(ForkingTestCase):

        @given(integers())
        def test_handles_abnormal_exit(self, x):
            os._exit(1)

    with pytest.raises(AbnormalExit):
        TestForking(
            'test_handles_abnormal_exit'
        ).test_handles_abnormal_exit()


def test_passes_exceptions_back():
    class TestForking(ForkingTestCase):

        @given(integers())
        def test_positive(self, x):
            assert x > 0

    with pytest.raises(AssertionError):
        TestForking(
            'test_positive'
        ).test_positive()


def test_captures_output_from_child():
    class TestForking(ForkingTestCase):

        @given(integers())
        def test_positive(self, x):
            assert x > 0

    with reporting.with_reporter(reporting.default):
        with capture_out() as out:
            with pytest.raises(AssertionError):
                TestForking(
                    'test_positive'
                ).test_positive()
        out = out.getvalue()
        assert 'Falsifying example: test_positive' in out
