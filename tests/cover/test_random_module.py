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

import random

import pytest

import hypothesis.strategies as st
from hypothesis import given, reporting
from tests.common.utils import capture_out


def test_can_seed_random():
    with capture_out() as out:
        with reporting.with_reporter(reporting.default):
            with pytest.raises(AssertionError):
                @given(st.random_module())
                def test(r):
                    assert False
                test()
    assert 'random.seed(0)' in out.getvalue()


@given(st.random_module(), st.random_module())
def test_seed_random_twice(r, r2):
    assert repr(r) == repr(r2)


@given(st.random_module())
def test_does_not_fail_health_check_if_randomness_is_used(r):
    import random
    random.getrandbits(128)


def test_reports_non_zero_seed():
    random.seed(0)
    zero_value = random.randint(0, 10)

    with capture_out() as out:
        with reporting.with_reporter(reporting.default):
            with pytest.raises(AssertionError):
                @given(st.integers())
                def test(r):
                    assert random.randint(0, 10) == zero_value
                test()
    assert 'random.seed' in out.getvalue()


def test_does_not_report_zero_seed():
    random.seed(0)
    zero_value = random.randint(0, 3)

    with capture_out() as out:
        with reporting.with_reporter(reporting.default):
            with pytest.raises(AssertionError):
                @given(st.integers())
                def test(r):
                    assert random.randint(0, 3) != zero_value
                test()
    assert 'random.seed' not in out.getvalue()
