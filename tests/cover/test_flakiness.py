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

import inspect

import pytest

from hypothesis import given, assume, Settings, Verbosity
from hypothesis.errors import Flaky, Unsatisfiable, UnsatisfiedAssumption
from hypothesis.strategies import lists, builds, booleans, integers, \
    random_module


def test_errors_even_if_does_not_error_on_final_call():
    @given(integers())
    def rude(x):
        assert not any(
            t[3] == u'best_satisfying_template'
            for t in inspect.getouterframes(inspect.currentframe())
        )

    with pytest.raises(Flaky):
        rude()


def test_gives_flaky_error_if_assumption_is_flaky():
    seen = set()

    @given(integers())
    @Settings(verbosity=Verbosity.quiet)
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


class DifferentReprEachTime(object):
    counter = 0

    def __repr__(self):
        DifferentReprEachTime.counter += 1
        return u'DifferentReprEachTime(%d)' % (DifferentReprEachTime.counter,)


def test_reports_repr_diff_in_flaky_error():
    @given(builds(DifferentReprEachTime))
    def rude(x):
        assert not any(
            t[3] == u'best_satisfying_template'
            for t in inspect.getouterframes(inspect.currentframe())
        )

    with pytest.raises(Flaky) as e:
        rude()
    assert u'Call 1:' in e.value.args[0]


class Nope(Exception):
    pass


def test_fails_only_once_is_flaky():
    first_call = [True]

    @given(integers())
    def test(x):
        if first_call[0]:
            first_call[0] = False
            assert False

    with pytest.raises(Flaky):
        test()


class SatisfyMe(Exception):
    pass


@given(lists(booleans()), lists(integers(1, 3)), random_module())
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
    @Settings(
        verbosity=Verbosity.quiet, database=None,
        perform_health_check=False,
    )
    def test(x):
        try:
            i = next(testit)
        except StopIteration:
            return
        if i == 1:
            return
        elif i == 2:
            assume(False)
        else:
            raise Nope()

    try:
        test()
    except (Nope, Unsatisfiable, Flaky):
        pass
    except UnsatisfiedAssumption:
        raise SatisfyMe()
