# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""This module provides the core primitives of Hypothesis, assume and given."""

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import time
import inspect
from random import Random
from itertools import islice
from collections import namedtuple

from hypothesis.extra import load_entry_points
from hypothesis.errors import Flaky, Timeout, Exhausted, Unfalsifiable, \
    Unsatisfiable, InvalidArgument, UnsatisfiedAssumption
from hypothesis.control import assume
from hypothesis.settings import Settings
from hypothesis.reporting import current_reporter
from hypothesis.specifiers import just
from hypothesis.internal.tracker import Tracker
from hypothesis.internal.reflection import arg_string, copy_argspec, \
    function_digest
from hypothesis.internal.examplesource import ParameterSource
from hypothesis.searchstrategy.strategies import BuildContext, strategy

[assume]


def time_to_call_it_a_day(settings, start_time):
    """Have we exceeded our timeout?"""
    if settings.timeout <= 0:
        return False
    return time.time() >= start_time + settings.timeout


def find_satisfying_template(
    search_strategy, random, condition, tracker, settings
):
    """Attempt to find a template for search_strategy such that condition is
    truthy.

    Exceptions other than UnsatisfiedAssumption will be immediately propagated.
    UnsatisfiedAssumption will indicate that similar examples should be avoided
    in future.

    Returns such a template as soon as it is found, otherwise stops after
    settings.max_examples examples have been considered or settings.timeout
    seconds have passed (if settings.timeout > 0).

    May raise a variety of exceptions depending on exact circumstances, but
    these will all subclass either Unsatisfiable (to indicate not enough
    examples were found which did not raise UnsatisfiedAssumption to consider
    this a valid test) or Unfalsifiable (to indicate that this probably means
    that condition is true with very high probability).

    """
    satisfying_examples = 0
    timed_out = False
    max_examples = settings.max_examples
    min_satisfying_examples = settings.min_satisfying_examples

    build_context = BuildContext(random)

    parameter_source = ParameterSource(
        context=build_context, strategy=search_strategy,
        min_parameters=max(2, int(float(max_examples) / 10))
    )
    start_time = time.time()

    for parameter in islice(
        parameter_source, max_examples - len(tracker)
    ):
        if len(tracker) >= search_strategy.size_upper_bound:
            break

        if time_to_call_it_a_day(settings, start_time):
            break

        example = search_strategy.produce_template(
            build_context, parameter
        )

        if tracker.track(example) > 1:
            parameter_source.mark_bad()
            continue
        try:
            if condition(example):
                return example
        except UnsatisfiedAssumption:
            parameter_source.mark_bad()
            continue
        satisfying_examples += 1
    run_time = time.time() - start_time
    timed_out = settings.timeout >= 0 and run_time >= settings.timeout
    if (
        satisfying_examples and
        len(tracker) >= search_strategy.size_lower_bound
    ):
        raise Exhausted(
            condition, satisfying_examples)
    elif satisfying_examples < min_satisfying_examples:
        if timed_out:
            raise Timeout(condition, satisfying_examples, run_time)
        else:
            raise Unsatisfiable(
                condition, satisfying_examples, run_time)
    else:
        raise Unfalsifiable(condition)


def simplify_template_such_that(search_strategy, random, t, f, tracker):
    """Perform a greedy search to produce a "simplest" version of a template
    that satisfies some predicate.

    Care is taken to avoid cycles in simplify.

    f should produce the same result deterministically. This function may
    raise an error given f such that f(t) returns False sometimes and True
    some other times.

    If f throws UnsatisfiedAssumption this will be treated the same as if
    it returned False.

    """
    assert isinstance(random, Random)

    yield t

    changed = True
    while changed:
        changed = False
        for simplify in search_strategy.simplifiers(t):
            while True:
                simpler = simplify(random, t)
                for s in simpler:
                    if tracker.track(s) > 1:
                        continue
                    try:
                        if f(s):
                            changed = True
                            yield s
                            t = s
                            break
                    except UnsatisfiedAssumption:
                        pass
                else:
                    break


def best_satisfying_template(
    search_strategy, random, condition, settings, storage
):
    """Find and then minimize a satisfying template.

    First look in storage if it is not None, then attempt to generate
    one. May throw all the exceptions of find_satisfying_template. Once
    an example has been found it will be further minimized.

    """
    tracker = Tracker()
    storage = None
    example_set = False
    start_time = time.time()

    if storage:
        for example in storage.fetch():
            tracker.track(example)
            if condition(example):
                satisfying_example = example
                example_set = True
                break

    if not example_set:
        satisfying_example = find_satisfying_template(
            search_strategy, random, condition, tracker, settings
        )

    for simpler in simplify_template_such_that(
        search_strategy, random, satisfying_example, condition, tracker
    ):
        satisfying_example = simpler
        if time_to_call_it_a_day(settings, start_time):
            break

    if storage is not None:
        storage.save(satisfying_example)

    return satisfying_example


HypothesisProvided = namedtuple('HypothesisProvided', ('value,'))


def given(*generator_arguments, **generator_kwargs):
    """A decorator for turning a test function that accepts arguments into a
    randomized test.

    This is the main entry point to Hypothesis. See the full tutorial
    for details of its behaviour.

    """

    # Keyword only arguments but actually supported in the full range of
    # pythons Hypothesis handles. pop so we don't later pick these up as
    # if they were keyword specifiers for data to pass to the test.
    provided_random = generator_kwargs.pop('random', None)
    settings = generator_kwargs.pop('settings', None) or Settings.default

    if (provided_random is not None) and settings.derandomize:
        raise InvalidArgument(
            'Cannot both be derandomized and provide an explicit random')

    if not (generator_arguments or generator_kwargs):
        raise InvalidArgument(
            'given must be called with at least one argument')

    def run_test_with_generator(test):
        if settings.derandomize:
            assert provided_random is None
            random = Random(
                function_digest(test)
            )
        else:
            random = provided_random or Random()

        original_argspec = inspect.getargspec(test)
        if original_argspec.varargs:
            raise InvalidArgument(
                'varargs are not supported with @given'
            )
        extra_kwargs = [
            k for k in generator_kwargs if k not in original_argspec.args]
        if extra_kwargs and not original_argspec.keywords:
            raise InvalidArgument(
                '%s() got an unexpected keyword argument %r' % (
                    test.__name__,
                    extra_kwargs[0]
                ))
        if (
            len(generator_arguments) > len(original_argspec.args)
        ):
            raise InvalidArgument((
                'Too many positional arguments for %s() (got %d but'
                ' expected at most %d') % (
                    test.__name__, len(generator_arguments),
                    len(original_argspec.args)))
        arguments = original_argspec.args + sorted(extra_kwargs)
        specifiers = list(generator_arguments)
        for a in arguments:
            if a in generator_kwargs:
                specifiers.append(generator_kwargs[a])

        argspec = inspect.ArgSpec(
            args=arguments,
            keywords=original_argspec.keywords,
            varargs=original_argspec.varargs,
            defaults=tuple(map(HypothesisProvided, specifiers))
        )

        @copy_argspec(
            test.__name__, argspec
        )
        def wrapped_test(*arguments, **kwargs):
            selfy = None
            # Because we converted all kwargs to given into real args and
            # error if we have neither args nor kwargs, this should always
            # be valid
            assert argspec.args
            selfy = kwargs.get(argspec.args[0])
            if isinstance(selfy, HypothesisProvided):
                selfy = None
            if selfy is not None:
                setup_example = getattr(selfy, 'setup_example', None)
                teardown_example = getattr(selfy, 'teardown_example', None)
            else:
                setup_example = None
                teardown_example = None

            setup_example = setup_example or (lambda: None)
            teardown_example = teardown_example or (lambda ex: None)

            if not any(
                isinstance(x, HypothesisProvided)
                for xs in (arguments, kwargs.values())
                for x in xs
            ):
                # All arguments have been satisfied without needing to invoke
                # hypothesis
                setup_example()
                try:
                    test(*arguments, **kwargs)
                finally:
                    teardown_example((arguments, kwargs))
                return

            def convert_to_specifier(v):
                if isinstance(v, HypothesisProvided):
                    return v.value
                else:
                    return just(v)

            given_specifier = (
                tuple(map(convert_to_specifier, arguments)),
                {k: convert_to_specifier(v) for k, v in kwargs.items()}
            )

            if settings.database:
                storage = settings.database.storage_for(given_specifier)
            else:
                storage = None

            search_strategy = strategy(given_specifier, settings)

            def is_template_example(xs):
                setup_example()
                example = None
                try:
                    example = search_strategy.reify(xs)
                    testargs, testkwargs = example
                    test(*testargs, **testkwargs)
                    return False
                except UnsatisfiedAssumption as e:
                    raise e
                except Exception:
                    return True
                finally:
                    teardown_example(example)

            is_template_example.__name__ = test.__name__
            is_template_example.__qualname__ = getattr(
                test, '__qualname__', test.__name__)

            try:
                falsifying_template = best_satisfying_template(
                    search_strategy, random, is_template_example,
                    settings, storage
                )
            except Unfalsifiable:
                return

            try:
                falsifying_example = None
                setup_example()
                falsifying_example = search_strategy.reify(falsifying_template)
                false_args, false_kwargs = falsifying_example
                current_reporter()(
                    'Falsifying example: %s(%s)' % (
                        test.__name__,
                        arg_string(
                            test,
                            false_args,
                            false_kwargs,
                        )
                    )
                )
                # We run this one final time so we get good errors
                # Otherwise we would have swallowed all the reports of it
                # actually having gone wrong.
                test(*false_args, **false_kwargs)

            finally:
                teardown_example(falsifying_example)

            # If we get here then something has gone wrong: We found a counter
            # example but it didn't fail when we invoked it again.
            raise Flaky(test, falsifying_example)
        wrapped_test.__name__ = test.__name__
        wrapped_test.__doc__ = test.__doc__
        wrapped_test.is_hypothesis_test = True
        return wrapped_test
    return run_test_with_generator


load_entry_points()
