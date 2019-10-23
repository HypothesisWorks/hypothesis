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

import hypothesis.strategies as st
from hypothesis import HealthCheck, Verbosity, given, settings as Settings
from hypothesis.errors import NoSuchExample, Unsatisfiable
from hypothesis.internal.conjecture.data import ConjectureData, StopTest
from hypothesis.internal.reflection import get_pretty_function_description
from tests.common.utils import no_shrink

TIME_INCREMENT = 0.01


class Timeout(BaseException):
    pass


def minimal(definition, condition=lambda x: True, settings=None, timeout_after=10):
    class Found(Exception):
        """Signal that the example matches condition."""

    def wrapped_condition(x):
        if timeout_after is not None:
            if runtime:
                runtime[0] += TIME_INCREMENT
                if runtime[0] >= timeout_after:
                    raise Timeout()
        result = condition(x)
        if result and not runtime:
            runtime.append(0.0)
        return result

    @given(definition)
    @Settings(
        parent=settings or Settings(max_examples=50000, verbosity=Verbosity.quiet),
        suppress_health_check=HealthCheck.all(),
        report_multiple_bugs=False,
        derandomize=True,
        database=None,
    )
    def inner(x):
        if wrapped_condition(x):
            result[:] = [x]
            raise Found

    definition.validate()
    runtime = []
    result = []
    try:
        inner()
    except Found:
        return result[0]
    raise Unsatisfiable(
        "Could not find any examples from %r that satisfied %s"
        % (definition, get_pretty_function_description(condition))
    )


def find_any(definition, condition=lambda _: True, settings=None):
    settings = settings or Settings.default
    return minimal(
        definition,
        condition,
        settings=Settings(
            settings, phases=no_shrink, max_examples=max(1000, settings.max_examples)
        ),
    )


def assert_no_examples(strategy, condition=lambda _: True):
    try:
        result = find_any(strategy, condition)
        assert False, "Expected no results but found %r" % (result,)
    except (Unsatisfiable, NoSuchExample):
        pass


def assert_all_examples(strategy, predicate):
    """Asserts that all examples of the given strategy match the predicate.

    :param strategy: Hypothesis strategy to check
    :param predicate: (callable) Predicate that takes example and returns bool
    """

    @given(strategy)
    def assert_examples(s):
        msg = "Found %r using strategy %s which does not match" % (s, strategy)
        assert predicate(s), msg

    assert_examples()


def assert_can_trigger_event(strategy, predicate):
    def test(buf):
        data = ConjectureData.for_buffer(buf)
        try:
            data.draw(strategy)
        except StopTest:
            pass
        return any(predicate(e) for e in data.events)

    find_any(st.binary(), test)
