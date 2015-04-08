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
from collections import namedtuple

from hypothesis.control import assume
from hypothesis.reporting import current_reporter
from hypothesis.specifiers import just
from hypothesis.errors import InvalidArgument, Flaky, Unfalsifiable, \
    UnsatisfiedAssumption
from hypothesis.settings import Settings
from hypothesis.internal.reflection import arg_string, copy_argspec
from hypothesis.utils.dynamicvariables import DynamicVariable
from itertools import islice

from hypothesis.extra import load_entry_points
from hypothesis.errors import Timeout, Exhausted, \
    Unsatisfiable
from hypothesis.internal.tracker import Tracker
from hypothesis.internal.reflection import function_digest
from hypothesis.internal.examplesource import ParameterSource
from hypothesis.searchstrategy.strategies import BuildContext, strategy


[assume]


def simplify_such_that(strategy, random, t, f, tracker=None):
    """Perform a greedy search to produce a "simplest" version of a
    template that satisfies some predicate.

    Care is taken to avoid cycles in simplify.

    f should produce the same result deterministically. This function may
    raise an error given f such that f(t) returns False sometimes and True
    some other times.

    """
    assert isinstance(random, Random)

    if tracker is None:
        tracker = Tracker()
    yield t

    changed = True
    while changed:
        changed = False
        for simplify in strategy.simplifiers(t):
            while True:
                simpler = simplify(random, t)
                for s in simpler:
                    if tracker.track(s) > 1:
                        continue
                    if f(s):
                        changed = True
                        yield s
                        t = s
                        break
                else:
                    break


class Verifier(object):

    """A wrapper object holding state required for a falsify invocation."""

    def __init__(
            self,
            random=None,
            settings=None,
    ):
        if settings is None:
            settings = Settings.default
        self.settings = settings
        self.database = settings.database

        self.min_satisfying_examples = settings.min_satisfying_examples
        self.max_examples = settings.max_examples
        self.timeout = settings.timeout
        if settings.derandomize and random:
            raise ValueError(
                'A verifier cannot both be derandomized and have a random '
                'generator')

        if settings.derandomize:
            self.random = None
        else:
            self.random = random or Random()

    def falsify(
            self,
            hypothesis,
            argument_type,
            **kwargs
    ):
        """
        Attempt to construct an example tuple x matching argument_types such
        that hypothesis(*x) returns a falsey value
        """
        teardown_example = kwargs.get('teardown_example') or (lambda x: None)
        setup_example = kwargs.get('setup_example') or (lambda: None)
        random = self.random
        if random is None:
            random = Random(
                function_digest(hypothesis)
            )

        build_context = BuildContext(random)

        search_strategy = strategy(argument_type, self.settings)
        storage = None
        if self.database is not None:
            storage = self.database.storage_for(argument_type)

        def falsifies(args):
            example = None
            try:
                try:
                    setup_example()
                    example = search_strategy.reify(args)
                    return not hypothesis(example)
                except UnsatisfiedAssumption:
                    return False
            finally:
                teardown_example(example)

        track_seen = Tracker()
        falsifying_examples = []
        if storage:
            for example in storage.fetch():
                track_seen.track(example)
                if falsifies(example):
                    falsifying_examples = [example]
                break

        satisfying_examples = 0
        timed_out = False
        max_examples = self.max_examples
        min_satisfying_examples = self.min_satisfying_examples

        parameter_source = ParameterSource(
            context=build_context, strategy=search_strategy,
            min_parameters=max(2, int(float(max_examples) / 10))
        )
        start_time = time.time()

        def time_to_call_it_a_day():
            """Have we exceeded our timeout?"""
            if self.timeout <= 0:
                return False
            return time.time() >= start_time + self.timeout

        for parameter in islice(
            parameter_source, max_examples - len(track_seen)
        ):
            if len(track_seen) >= search_strategy.size_upper_bound:
                break

            if falsifying_examples:
                break
            if time_to_call_it_a_day():
                break

            args = search_strategy.produce_template(
                build_context, parameter
            )

            if track_seen.track(args) > 1:
                parameter_source.mark_bad()
                continue
            try:
                setup_example()
                a = None
                try:
                    a = search_strategy.reify(args)
                    is_falsifying_example = not hypothesis(a)
                finally:
                    teardown_example(a)
            except UnsatisfiedAssumption:
                parameter_source.mark_bad()
                continue
            satisfying_examples += 1
            if is_falsifying_example:
                falsifying_examples.append(args)
        run_time = time.time() - start_time
        timed_out = self.timeout >= 0 and run_time >= self.timeout
        if not falsifying_examples:
            if (
                satisfying_examples and
                len(track_seen) >= search_strategy.size_lower_bound
            ):
                raise Exhausted(
                    hypothesis, satisfying_examples)
            elif satisfying_examples < min_satisfying_examples:
                if timed_out:
                    raise Timeout(hypothesis, satisfying_examples, run_time)
                else:
                    raise Unsatisfiable(
                        hypothesis, satisfying_examples, run_time)
            else:
                raise Unfalsifiable(hypothesis)

        for example in falsifying_examples:
            if not falsifies(example):
                raise Flaky(hypothesis, example)

        best_example = falsifying_examples[0]

        for simpler in simplify_such_that(
            search_strategy,
            random,
            best_example, falsifies,
            tracker=track_seen,
        ):
            best_example = simpler
            if time_to_call_it_a_day():
                # We no cover in here because it's a bit sensitive to timing
                # and tends to make tests flaky. There are tests that mean
                # this is definitely covered most of the time.
                break  # pragma: no cover

        if storage is not None:
            storage.save(best_example)

        setup_example()
        return search_strategy.reify(best_example)


load_entry_points()
HypothesisProvided = namedtuple('HypothesisProvided', ('value,'))


_debugging_return_failing_example = DynamicVariable(False)


def given(*generator_arguments, **generator_kwargs):
    """A decorator for turning a test function that accepts arguments into a
    randomized test.

    This is the main entry point to Hypothesis. See the full tutorial
    for details of its behaviour.

    """
    if 'verifier' in generator_kwargs:
        verifier = generator_kwargs.pop('verifier')
        verifier.start_time = time.time()
    else:
        verifier = Verifier(
            settings=generator_kwargs.pop('settings', None),
            random=generator_kwargs.pop('random', None),
        )

    if not (generator_arguments or generator_kwargs):
        raise InvalidArgument(
            'given must be called with at least one argument')

    def run_test_with_generator(test):
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

            def to_falsify(xs):
                testargs, testkwargs = xs
                try:
                    test(*testargs, **testkwargs)
                    return True
                except UnsatisfiedAssumption as e:
                    raise e
                except Exception:
                    return False

            to_falsify.__name__ = test.__name__
            to_falsify.__qualname__ = getattr(
                test, '__qualname__', test.__name__)

            if _debugging_return_failing_example.value:
                return verifier.falsify(
                    to_falsify, given_specifier,
                    setup_example=setup_example,
                    teardown_example=teardown_example,
                )

            try:
                falsifying_example = verifier.falsify(
                    to_falsify, given_specifier,
                    setup_example=setup_example,
                    teardown_example=teardown_example,
                )
            except Unfalsifiable:
                return

            try:
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
        wrapped_test.verifier = verifier
        wrapped_test.is_hypothesis_test = True
        return wrapped_test
    return run_test_with_generator
