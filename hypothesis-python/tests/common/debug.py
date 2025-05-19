# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from unittest import SkipTest

from hypothesis import HealthCheck, Phase, Verbosity, given, settings as Settings
from hypothesis._settings import local_settings
from hypothesis.control import _current_build_context
from hypothesis.errors import Found, NoSuchExample, Unsatisfiable
from hypothesis.internal.reflection import get_pretty_function_description

from tests.common.utils import no_shrink

TIME_INCREMENT = 0.00001


def minimal(definition, condition=lambda x: True, settings=None):
    from tests.conftest import in_shrinking_benchmark

    definition.validate()
    result = None

    def wrapped_condition(x):
        # This sure seems pointless, but `test_sum_of_pair` fails otherwise...
        return condition(x)

    if (
        context := _current_build_context.value
    ) and context.data.provider.avoid_realization:
        raise SkipTest("`minimal()` helper not supported under symbolic execution")

    if settings is None:
        settings = Settings(max_examples=500, phases=(Phase.generate, Phase.shrink))

    verbosity = settings.verbosity
    if verbosity == Verbosity.normal:
        verbosity = Verbosity.quiet

    @given(definition)
    @Settings(
        parent=settings,
        suppress_health_check=list(HealthCheck),
        report_multiple_bugs=False,
        # we derandomize in general to avoid flaky tests, but we do want to
        # measure this variation while benchmarking.
        derandomize=not in_shrinking_benchmark,
        database=None,
        verbosity=verbosity,
    )
    def inner(x):
        if wrapped_condition(x):
            nonlocal result
            result = x
            raise Found

    try:
        inner()
    except Found:
        return result
    raise Unsatisfiable(
        f"Could not find any examples from {definition!r} that satisfied "
        f"{get_pretty_function_description(condition)}"
    )


def find_any(definition, condition=lambda _: True, settings=None):
    # If nested within an existing @given
    if context := _current_build_context.value:
        while True:
            if condition(s := context.data.draw(definition)):
                return s

    # If top-level
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
        assert_all_examples(strategy, lambda val: not condition(val))
    except (Unsatisfiable, NoSuchExample):
        pass


def assert_all_examples(strategy, predicate, settings=None):
    """Asserts that all examples of the given strategy match the predicate.

    :param strategy: Hypothesis strategy to check
    :param predicate: (callable) Predicate that takes example and returns bool
    """
    if context := _current_build_context.value:
        with local_settings(Settings(parent=settings)):
            for _ in range(20):
                s = context.data.draw(strategy)
                msg = f"Found {s!r} using strategy {strategy} which does not match"
                assert predicate(s), msg

    else:

        @given(strategy)
        @Settings(parent=settings, database=None)
        def assert_examples(s):
            msg = f"Found {s!r} using strategy {strategy} which does not match"
            assert predicate(s), msg

        assert_examples()


def assert_simple_property(strategy, predicate, settings=None):
    """Like assert_all_examples, intended as a self-documenting shortcut for simple constant
    properties (`is`, `isinstance`, `==`, ...) that can be adequately verified in just a few
    examples.

    For more thorough checking, use assert_all_examples.
    """

    assert_all_examples(
        strategy,
        predicate,
        Settings(
            parent=settings,
            max_examples=15,
            suppress_health_check=list(HealthCheck),
        ),
    )


def check_can_generate_examples(strategy, settings=None):
    """Tries to generate a small number of examples from the strategy, to verify that it can
    do so without raising.

    Nothing is returned, it only checks that no error is raised.
    """

    assert_simple_property(
        strategy,
        lambda _: True,
        settings=Settings(
            parent=settings,
            phases=(Phase.generate,),
        ),
    )
