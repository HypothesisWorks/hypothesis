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

import hypothesis.core as core
import hypothesis.strategies as st
from hypothesis import given
from hypothesis.errors import FailedHealthCheck
from tests.common.utils import capture_out
from hypothesis.internal.compat import hrange


@pytest.mark.parametrize('in_pytest', [False, True])
@pytest.mark.parametrize('fail_healthcheck', [False, True])
def test_prints_seed_on_exception(monkeypatch, in_pytest, fail_healthcheck):
    monkeypatch.setattr(core, 'running_under_pytest', in_pytest)

    strategy = st.integers()
    if fail_healthcheck:
        def slow_map(i):
            time.sleep(10)
            return i
        strategy = strategy.map(slow_map)
        expected_exc = FailedHealthCheck
    else:
        expected_exc = AssertionError

    @given(strategy)
    def test(i):
        assert False

    with capture_out() as o:
        with pytest.raises(expected_exc):
            test()

    output = o.getvalue()

    seed = test._hypothesis_internal_use_generated_seed
    assert seed is not None
    assert '@seed(%d)' % (seed,) in output
    contains_pytest_instruction = ('--hypothesis-seed=%d' % (seed,)) in output
    assert contains_pytest_instruction == in_pytest


def test_uses_global_force(monkeypatch):
    monkeypatch.setattr(core, 'global_force_seed', 42)

    @given(st.integers())
    def test(i):
        raise ValueError()

    output = []

    for _ in hrange(2):
        with capture_out() as o:
            with pytest.raises(ValueError):
                test()
        output.append(o.getvalue())

    assert output[0] == output[1]
    assert '@seed' not in output[0]
