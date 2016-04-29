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

import pytest

from hypothesis import given, assume, reject, example, settings, Verbosity
from hypothesis.errors import Flaky, Unsatisfiable, UnsatisfiedAssumption
from hypothesis.strategies import lists, booleans, integers, composite, \
    random_module


class Nope(Exception):
    pass


def test_fails_only_once_is_flaky():
    first_call = [True]

    @given(integers())
    def rude(x):
        if first_call[0]:
            first_call[0] = False
            raise Nope()

    with pytest.raises(Flaky):
        rude()


def test_gives_flaky_error_if_assumption_is_flaky():
    seen = set()

    @given(integers())
    @settings(verbosity=Verbosity.quiet)
    def oops(s):
        assume(s not in seen)
        seen.add(s)
        assert False

    with pytest.raises(Flaky):
        oops()


def test_does_not_attempt_to_shrink_flaky_errors():
    values = []

    @given(integers())
    def test(x):
        values.append(x)
        assert len(values) != 1
    with pytest.raises(Flaky):
        test()
    assert len(set(values)) == 1


class SatisfyMe(Exception):
    pass


@composite
def single_bool_lists(draw):
    n = draw(integers(0, 20))
    result = [False] * (n + 1)
    result[n] = True
    return result


@example([True, False, False, False], [3], None,)
@example([False, True, False, False], [3], None,)
@example([False, False, True, False], [3], None,)
@example([False, False, False, True], [3], None,)
@settings(max_examples=0)
@given(
    lists(booleans(), average_size=20) | single_bool_lists(),
    lists(integers(1, 3), average_size=20), random_module())
def test_failure_sequence_inducing(building, testing, rnd):
    buildit = iter(building)
    testit = iter(testing)

    def build(x):
        try:
            assume(not next(buildit))
        except StopIteration:
            pass
        return x

    @given(integers().map(build))
    @settings(
        verbosity=Verbosity.quiet, database=None,
        perform_health_check=False, max_shrinks=0
    )
    def test(x):
        try:
            i = next(testit)
        except StopIteration:
            return
        if i == 1:
            return
        elif i == 2:
            reject()
        else:
            raise Nope()

    try:
        test()
    except (Nope, Unsatisfiable, Flaky):
        pass
    except UnsatisfiedAssumption:
        raise SatisfyMe()
