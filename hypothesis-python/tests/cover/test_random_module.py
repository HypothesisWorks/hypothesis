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

import random

import pytest

import hypothesis.strategies as st
from hypothesis import given, register_random, reporting
from hypothesis.errors import InvalidArgument
from hypothesis.internal import entropy
from tests.common.utils import capture_out


def test_can_seed_random():
    with capture_out() as out:
        with reporting.with_reporter(reporting.default):
            with pytest.raises(AssertionError):

                @given(st.random_module())
                def test(r):
                    assert False

                test()
    assert "RandomSeeder(0)" in out.getvalue()


@given(st.random_module(), st.random_module())
def test_seed_random_twice(r, r2):
    assert repr(r) == repr(r2)


@given(st.random_module())
def test_does_not_fail_health_check_if_randomness_is_used(r):
    random.getrandbits(128)


def test_cannot_register_non_Random():
    with pytest.raises(InvalidArgument):
        register_random("not a Random instance")


def test_registering_a_Random_is_idempotent():
    r = random.Random()
    register_random(r)
    register_random(r)
    assert entropy.RANDOMS_TO_MANAGE.pop() is r
    assert r not in entropy.RANDOMS_TO_MANAGE


def test_manages_registered_Random_instance():
    r = random.Random()
    register_random(r)
    state = r.getstate()
    result = []

    @given(st.integers())
    def inner(x):
        v = r.random()
        if result:
            assert v == result[0]
        else:
            result.append(v)

    inner()
    assert state == r.getstate()

    entropy.RANDOMS_TO_MANAGE.remove(r)
    assert r not in entropy.RANDOMS_TO_MANAGE


def test_registered_Random_is_seeded_by_random_module_strategy():
    r = random.Random()
    register_random(r)
    state = r.getstate()
    results = set()
    count = [0]

    @given(st.integers())
    def inner(x):
        results.add(r.random())
        count[0] += 1

    inner()
    assert count[0] > len(results) * 0.9, "too few unique random numbers"
    assert state == r.getstate()

    entropy.RANDOMS_TO_MANAGE.remove(r)
    assert r not in entropy.RANDOMS_TO_MANAGE
