# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
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
from hypothesis import given, settings
from hypothesis.errors import FailedHealthCheck
from tests.common.utils import capture_out


def test_slow_generation_fails_a_health_check():
    @given(st.integers().map(lambda x: time.sleep(0.2)))
    def test(x):
        pass

    with raises(FailedHealthCheck):
        test()


def test_global_random_in_strategy_fails_a_health_check():
    import random

    @given(st.lists(st.integers(), min_size=1).map(random.choice))
    def test(x):
        pass

    with raises(FailedHealthCheck):
        test()


def test_warns_if_settings_are_not_strict(recwarn):
    import random

    with settings(strict=False):
        @given(st.lists(st.integers(), min_size=1))
        def test(x):
            random.choice(x)

    test()
    assert recwarn.pop(FailedHealthCheck) is not None
    with raises(AssertionError):
        recwarn.pop(FailedHealthCheck)


def test_does_not_repeat_random_warnings(recwarn):
    import random

    with settings(strict=False):
        @given(st.lists(st.integers(), min_size=1).map(random.choice))
        def test(x):
            pass

    test()
    assert recwarn.pop(FailedHealthCheck) is not None
    with raises(AssertionError):
        recwarn.pop(FailedHealthCheck)


def test_global_random_in_test_fails_a_health_check():
    import random

    @given(st.lists(st.integers(), min_size=1))
    def test(x):
        random.choice(x)

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


def test_error_in_strategy_produces_only_one_traceback():
    def boom(x):
        raise ValueError()

    with settings(strict=False):
        @given(st.integers().map(boom))
        def test(x):
            pass

        with raises(ValueError):
            with reporting.with_reporter(reporting.default):
                with capture_out() as out:
                    test()
    assert out.getvalue().count('ValueError') == 2


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


def test_filtering_most_things_fails_a_health_check():
    @given(st.integers().filter(lambda x: x % 100 == 0))
    @settings(database=None)
    def test(x):
        pass

    with raises(FailedHealthCheck) as e:
        test()
    assert 'filter' in e.value.args[0]


def test_broad_recursive_data_will_fail_a_health_check():
    r = st.recursive(
        st.integers(), lambda s: st.tuples(*((s,) * 10)),
    )

    @given(st.tuples(r, r, r, r, r, r, r))
    @settings(database=None)
    def test(x):
        pass

    with raises(FailedHealthCheck) as e:
        test()
    assert 'allowable size' in e.value.args[0]


def test_health_check_runs_should_not_affect_determinism(recwarn):
    with settings(
        strict=False, timeout=0, max_examples=2, derandomize=True,
        database=None, perform_health_check=True,
    ):
        values = []
        t = 0.25

        @given(st.integers().map(lambda i: [time.sleep(t), i][1]))
        @settings(database=None)
        def test(x):
            values.append(x)

        test()
        recwarn.pop(FailedHealthCheck)
        v1 = values
        values = []
        t = 0
        test()
        assert v1 == values


def test_nesting_without_control_fails_health_check():
    @given(st.integers())
    def test_blah(x):
        @given(st.integers())
        def test_nest(y):
            assert y < x
        with raises(AssertionError):
            test_nest()
    with raises(FailedHealthCheck):
        test_blah()


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
