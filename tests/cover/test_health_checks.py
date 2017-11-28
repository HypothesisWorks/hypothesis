# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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
from pytest import raises

import hypothesis.strategies as st
from hypothesis import HealthCheck, given, settings
from hypothesis.errors import InvalidArgument, FailedHealthCheck
from hypothesis.control import assume
from tests.common.utils import checks_deprecated_behaviour
from hypothesis.internal.compat import int_from_bytes
from hypothesis.searchstrategy.strategies import SearchStrategy


def test_slow_generation_fails_a_health_check():
    @given(st.integers().map(lambda x: time.sleep(0.2)))
    def test(x):
        pass

    with raises(FailedHealthCheck):
        test()


def test_slow_generation_inline_fails_a_health_check():
    @settings(deadline=None)
    @given(st.data())
    def test(data):
        data.draw(st.integers().map(lambda x: time.sleep(0.2)))

    with raises(FailedHealthCheck):
        test()


def test_default_health_check_can_weaken_specific():
    import random

    @given(st.lists(st.integers(), min_size=1))
    def test(x):
        random.choice(x)

    with settings(perform_health_check=False):
        test()


def test_suppressing_filtering_health_check():
    count = [0]

    def too_soon(x):
        count[0] += 1
        return count[0] >= 200

    @given(st.integers().filter(too_soon))
    def test1(x):
        raise ValueError()

    with raises(FailedHealthCheck):
        test1()

    count[0] = 0

    @settings(suppress_health_check=[
        HealthCheck.filter_too_much, HealthCheck.too_slow])
    @given(st.integers().filter(too_soon))
    def test2(x):
        raise ValueError()

    with raises(ValueError):
        test2()


def test_filtering_everything_fails_a_health_check():
    @given(st.integers().filter(lambda x: False))
    @settings(database=None)
    def test(x):
        pass

    with raises(FailedHealthCheck) as e:
        test()
    assert 'filter' in e.value.args[0]


class fails_regularly(SearchStrategy):

    def do_draw(self, data):
        b = int_from_bytes(data.draw_bytes(2))
        assume(b == 3)
        print('ohai')


@settings(max_shrinks=0)
def test_filtering_most_things_fails_a_health_check():
    @given(fails_regularly())
    @settings(database=None)
    def test(x):
        pass

    with raises(FailedHealthCheck) as e:
        test()
    assert 'filter' in e.value.args[0]


def test_large_data_will_fail_a_health_check():
    @given(st.lists(st.binary(min_size=1024, max_size=1024), average_size=100))
    @settings(database=None, buffer_size=1000)
    def test(x):
        pass

    with raises(FailedHealthCheck) as e:
        test()
    assert 'allowable size' in e.value.args[0]


def test_returning_non_none_is_forbidden():
    @given(st.integers())
    def a(x):
        return 1

    with raises(FailedHealthCheck):
        a()


def test_a_very_slow_test_will_fail_a_health_check():
    @given(st.integers())
    @settings(deadline=None)
    def a(x):
        time.sleep(1000)
    with raises(FailedHealthCheck):
        a()


def test_the_slow_test_health_check_can_be_disabled():
    @given(st.integers())
    @settings(suppress_health_check=[
        HealthCheck.hung_test,
    ], deadline=None)
    def a(x):
        time.sleep(1000)
    a()


def test_the_slow_test_health_only_runs_if_health_checks_are_on():
    @given(st.integers())
    @settings(perform_health_check=False, deadline=None)
    def a(x):
        time.sleep(1000)
    a()


def test_returning_non_none_does_not_fail_if_health_check_disabled():
    @given(st.integers())
    @settings(perform_health_check=False)
    def a(x):
        return 1

    a()


def test_large_base_example_fails_health_check():
    @given(st.binary(min_size=7000, max_size=7000))
    def test(b):
        pass

    with pytest.raises(FailedHealthCheck) as exc:
        test()

    assert exc.value.health_check == HealthCheck.large_base_example


def test_example_that_shrinks_to_overrun_fails_health_check():
    @given(st.binary(min_size=9000, max_size=9000) | st.none())
    def test(b):
        pass

    with pytest.raises(FailedHealthCheck) as exc:
        test()

    assert exc.value.health_check == HealthCheck.large_base_example


@pytest.mark.parametrize(
    'check', [HealthCheck.random_module, HealthCheck.exception_in_generation])
@checks_deprecated_behaviour
def test_noop_health_checks(check):
    settings(suppress_health_check=[check])


def test_it_is_an_error_to_suppress_non_iterables():
    with raises(InvalidArgument):
        settings(suppress_health_check=1)


@checks_deprecated_behaviour
def test_is_is_deprecated_to_suppress_non_healthchecks():
    settings(suppress_health_check=[1])
