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

import sys

from hypothesis import settings as Settings
from hypothesis import find, given, assume, reject
from hypothesis.errors import NoSuchExample, Unsatisfiable

TIME_INCREMENT = 0.01


class Timeout(BaseException):
    pass


def minimal(
        definition, condition=None,
        settings=None, timeout_after=10, random=None
):
    settings = Settings(
        settings,
        max_examples=50000,
        max_iterations=100000,
        max_shrinks=5000,
        database=None,
    )

    runtime = []

    if condition is None:
        def condition(x):
            return True

    def wrapped_condition(x):
        if runtime:
            runtime[0] += TIME_INCREMENT
            if runtime[0] >= timeout_after:
                raise Timeout()
        result = condition(x)
        if result and not runtime:
            runtime.append(0.0)
        return result

    try:
        orig = sys.gettrace()
        return find(
            definition,
            wrapped_condition,
            settings=settings,
            random=random,
        )
    finally:
        sys.settrace(orig)


def find_any(
        definition, condition=None,
        settings=None, random=None
):
    settings = Settings(
        settings,
        max_examples=10000,
        max_iterations=10000,
        max_shrinks=0000,
        database=None,
    )

    if condition is None:
        def condition(x):
            return True

    return find(
        definition,
        condition,
        settings=settings,
        random=random,
    )


def assert_no_examples(strategy, condition=None):
    if condition is None:
        def predicate(x):
            reject()
    else:
        def predicate(x):
            assume(condition(x))

    try:
        result = find(
            strategy, predicate,
            settings=Settings(max_iterations=100, max_shrinks=1)
        )
        assert False, 'Expected no results but found %r' % (result,)
    except (Unsatisfiable, NoSuchExample):
        pass


def assert_all_examples(strategy, predicate):
    """Asserts that all examples of the given strategy match the predicate.

    :param strategy: Hypothesis strategy to check
    :param predicate: (callable) Predicate that takes example and returns bool

    """
    @given(strategy)
    def assert_examples(s):
        assert predicate(s), \
            'Found %r using strategy %s which does not match' % (s, strategy)

    assert_examples()
