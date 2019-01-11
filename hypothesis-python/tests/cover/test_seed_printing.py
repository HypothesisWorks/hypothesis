# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import time

import pytest

import hypothesis.core as core
import hypothesis.strategies as st
from hypothesis import Verbosity, assume, given, settings
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.errors import FailedHealthCheck
from hypothesis.internal.compat import hrange
from tests.common.utils import all_values, capture_out


@pytest.mark.parametrize("in_pytest", [False, True])
@pytest.mark.parametrize("fail_healthcheck", [False, True])
@pytest.mark.parametrize("verbosity", [Verbosity.normal, Verbosity.quiet])
def test_prints_seed_only_on_healthcheck(
    monkeypatch, in_pytest, fail_healthcheck, verbosity
):
    monkeypatch.setattr(core, "running_under_pytest", in_pytest)

    strategy = st.integers()
    if fail_healthcheck:

        def slow_map(i):
            time.sleep(10)
            return i

        strategy = strategy.map(slow_map)
        expected_exc = FailedHealthCheck
    else:
        expected_exc = AssertionError

    @settings(database=None, verbosity=verbosity)
    @given(strategy)
    def test(i):
        assert fail_healthcheck

    with capture_out() as o:
        with pytest.raises(expected_exc):
            test()

    output = o.getvalue()

    seed = test._hypothesis_internal_use_generated_seed
    assert seed is not None
    if fail_healthcheck and verbosity != Verbosity.quiet:
        assert "@seed(%d)" % (seed,) in output
        contains_pytest_instruction = ("--hypothesis-seed=%d" % (seed,)) in output
        assert contains_pytest_instruction == in_pytest
    else:
        assert "@seed" not in output
        assert "--hypothesis-seed=%d" % (seed,) not in output


def test_uses_global_force(monkeypatch):
    monkeypatch.setattr(core, "global_force_seed", 42)

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
    assert "@seed" not in output[0]


def test_does_print_on_reuse_from_database():
    passes_healthcheck = False

    database = InMemoryExampleDatabase()

    @settings(database=database)
    @given(st.integers())
    def test(i):
        assume(passes_healthcheck)
        raise ValueError()

    with capture_out() as o:
        with pytest.raises(FailedHealthCheck):
            test()

    assert "@seed" in o.getvalue()

    passes_healthcheck = True

    with capture_out() as o:
        with pytest.raises(ValueError):
            test()

    assert all_values(database)
    assert "@seed" not in o.getvalue()

    passes_healthcheck = False

    with capture_out() as o:
        with pytest.raises(FailedHealthCheck):
            test()

    assert "@seed" in o.getvalue()
