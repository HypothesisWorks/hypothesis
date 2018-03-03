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

import gc
import sys
import time as time_module

import pytest

from tests.common import TIME_INCREMENT
from tests.common.setup import run
from hypothesis.internal.coverage import IN_COVERAGE_TESTS

run()


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'slow: pandas expects this marker to exist.')


@pytest.fixture(scope=u'function', autouse=True)
def gc_before_each_test():
    gc.collect()


@pytest.fixture(scope=u'function', autouse=True)
def consistently_increment_time(monkeypatch):
    """Rather than rely on real system time we monkey patch time.time so that
    it passes at a consistent rate between calls.

    The reason for this is that when these tests run on travis, performance is
    extremely variable and the VM the tests are on might go to sleep for a bit,
    introducing arbitrary delays. This can cause a number of tests to fail
    flakily.

    Replacing time with a fake version under our control avoids this problem.
    """
    frozen = [False]

    current_time = [time_module.time()]

    def time():
        if not frozen[0]:
            current_time[0] += TIME_INCREMENT
        return current_time[0]

    def sleep(naptime):
        current_time[0] += naptime

    def freeze():
        frozen[0] = True

    monkeypatch.setattr(time_module, 'time', time)
    try:
        monkeypatch.setattr(time_module, 'monotonic', time)
    except AttributeError:
        assert sys.version_info[0] == 2
    monkeypatch.setattr(time_module, 'sleep', sleep)
    monkeypatch.setattr(time_module, 'freeze', freeze, raising=False)


if not IN_COVERAGE_TESTS:
    @pytest.fixture(scope=u'function', autouse=True)
    def validate_lack_of_trace_function():
        assert sys.gettrace() is None
