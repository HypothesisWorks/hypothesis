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

import time

from pytest import raises

import hypothesis.reporting as reporting
import hypothesis.strategies as st
from hypothesis import given, settings, HealthCheck
from hypothesis.errors import FailedHealthCheck
from hypothesis.control import assume
from tests.common.utils import capture_out
from hypothesis.internal.compat import int_from_bytes
from hypothesis.searchstrategy.strategies import SearchStrategy


def test_slow_generation_fails_a_health_check():
    @given(st.integers().map(lambda x: time.sleep(0.2)))
    def test(x):
        pass

    with raises(FailedHealthCheck):
        test()


def test_default_health_check_can_weaken_specific():
    import random

    @given(st.lists(st.integers(), min_size=1))
    def test(x):
        random.choice(x)

    with settings(perform_health_check=False):
        test()


def test_error_in_strategy_produces_health_check_error():
    def boom(x):
        raise ValueError()

    @given(st.integers().map(boom))
    def test(x):
        pass

    with raises(FailedHealthCheck) as e:
        with reporting.with_reporter(reporting.default):
            test()
    assert 'executor' not in e.value.args[0]


def test_suppressing_error_in_value_generation():
    def boom(x):
        raise ValueError()

    @settings(suppress_health_check=[HealthCheck.exception_in_generation])
    @given(st.integers().map(boom))
    def test(x):
        pass

    with capture_out() as out:
        with reporting.with_reporter(reporting.default):
            with raises(ValueError):
                test()
    assert 'ValueError' not in out.getvalue()


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


def test_error_in_strategy_with_custom_executor():
    def boom(x):
        raise ValueError()

    class Foo(object):

        def execute_example(self, f):
            return f()

        @given(st.integers().map(boom))
        @settings(database=None)
        def test(self, x):
            pass

    with raises(FailedHealthCheck) as e:
        Foo().test()
    assert 'executor' in e.value.args[0]


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


def test_returning_non_none_does_not_fail_if_health_check_disabled():
    @given(st.integers())
    @settings(perform_health_check=False)
    def a(x):
        return 1

    a()
