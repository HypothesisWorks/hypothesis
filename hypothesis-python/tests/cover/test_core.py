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

import time

import pytest
from flaky import flaky
from _pytest.outcomes import Failed, Skipped

import hypothesis.strategies as s
from hypothesis import find, given, reject, settings
from hypothesis.errors import NoSuchExample, Unsatisfiable
from tests.common.utils import checks_deprecated_behaviour


def test_stops_after_max_examples_if_satisfying():
    tracker = []

    def track(x):
        tracker.append(x)
        return False

    max_examples = 100

    with pytest.raises(NoSuchExample):
        find(
            s.integers(0, 10000),
            track, settings=settings(max_examples=max_examples))

    assert len(tracker) == max_examples


def test_stops_after_ten_times_max_examples_if_not_satisfying():
    count = [0]

    def track(x):
        count[0] += 1
        reject()

    max_examples = 100

    with pytest.raises(Unsatisfiable):
        find(
            s.integers(0, 10000),
            track, settings=settings(max_examples=max_examples))

    assert count[0] == 10 * max_examples


@checks_deprecated_behaviour
@flaky(min_passes=1, max_runs=2)
def test_can_time_out_in_simplify():
    def slow_always_true(x):
        time.sleep(0.1)
        return True
    start = time.time()
    find(
        s.lists(s.booleans()), slow_always_true,
        settings=settings(timeout=0.1, database=None)
    )
    finish = time.time()
    run_time = finish - start
    assert run_time <= 0.4


some_normal_settings = settings()


def test_is_not_normally_default():
    assert settings.default is not some_normal_settings


@given(s.booleans())
@some_normal_settings
def test_settings_are_default_in_given(x):
    assert settings.default is some_normal_settings


def test_given_shrinks_pytest_helper_errors():
    final_value = [None]

    @given(s.integers())
    def inner(x):
        final_value[0] = x
        if x > 100:
            pytest.fail('x=%r is too big!' % x)

    with pytest.raises(Failed):
        inner()
    assert final_value[0] == 101


def test_pytest_skip_skips_shrinking():
    values = []

    @given(s.integers())
    def inner(x):
        values.append(x)
        if x > 100:
            pytest.skip('x=%r is too big!' % x)

    with pytest.raises(Skipped):
        inner()
    assert len([x for x in values if x > 100]) == 1
