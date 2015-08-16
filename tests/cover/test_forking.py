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

import os

import pytest
import hypothesis.reporting as reporting
from hypothesis import given, assume
from hypothesis.errors import AbnormalExit
from tests.common.utils import capture_out
from hypothesis.strategies import sets, booleans, integers

ForkingTestCase = pytest.importorskip(
    u'hypothesis.testrunners.forking'
).ForkingTestCase


def test_runs_normally_if_no_failure():
    class Foo(ForkingTestCase):

        @given(sets(booleans()))
        def runs_normally(self, x):
            pass

    Foo(u'runs_normally').runs_normally()


def test_can_assume_in_a_fork():
    class Foo(ForkingTestCase):

        @given(booleans())
        def only_true(self, x):
            assume(x)
    Foo(u'only_true').only_true()


def test_raises_abnormal_exit_if_bad_pickle_in_exception():
    class Boo(Exception):

        def __getstate__(self):
            raise ValueError()

    class TestBoo(ForkingTestCase):

        @given(integers())
        def test_boo(self, x):
            raise Boo()

    with pytest.raises(AbnormalExit):
        TestBoo(u'test_boo').test_boo()


def test_raises_abnormal_exit_on_premature_child_death():
    class TestForking(ForkingTestCase):

        @given(integers())
        def test_handles_abnormal_exit(self, x):
            os._exit(1)

    with pytest.raises(AbnormalExit):
        TestForking(
            u'test_handles_abnormal_exit'
        ).test_handles_abnormal_exit()


def test_passes_exceptions_back():
    class TestForking(ForkingTestCase):

        @given(integers())
        def test_positive(self, x):
            assert x > 0

    with pytest.raises(AssertionError):
        TestForking(
            u'test_positive'
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
                    u'test_positive'
                ).test_positive()
        out = out.getvalue()
        assert u'Falsifying example: test_positive' in out


def test_captures_output_from_child_under_abnormal_exit():
    class TestForking(ForkingTestCase):

        @given(integers())
        def test_death(self, x):
            os._exit(1)

    with reporting.with_reporter(reporting.default):
        with capture_out() as out:
            with pytest.raises(AbnormalExit):
                TestForking(
                    u'test_death'
                ).test_death()
        out = out.getvalue()
        assert u'Falsifying example: test_death' in out
