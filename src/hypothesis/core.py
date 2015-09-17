# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""This module provides the core primitives of Hypothesis, assume and given."""


from __future__ import division, print_function, absolute_import

import math
import time
import inspect
import binascii
import functools
import traceback
from random import Random
from itertools import islice
from collections import namedtuple

import hypothesis.strategies as sd
from hypothesis.extra import load_entry_points
from hypothesis.errors import Flaky, Timeout, NoSuchExample, \
    Unsatisfiable, BadTemplateDraw, InvalidArgument, \
    UnsatisfiedAssumption, DefinitelyNoSuchExample
from hypothesis.control import assume  # noqa
from hypothesis.control import BuildContext
from hypothesis.settings import Settings, Verbosity
from hypothesis.executors import executor
from hypothesis.reporting import report, debug_report, verbose_report, \
    current_verbosity
from hypothesis.deprecation import note_deprecation
from hypothesis.internal.compat import qualname, getargspec, \
    unicode_safe_repr
from hypothesis.internal.tracker import Tracker
from hypothesis.internal.reflection import arg_string, copy_argspec, \
    function_digest, fully_qualified_name, convert_positional_arguments, \
    get_pretty_function_description
from hypothesis.internal.examplesource import ParameterSource
from hypothesis.searchstrategy.strategies import strategy


def time_to_call_it_a_day(settings, start_time):
    """Have we exceeded our timeout?"""
    if settings.timeout <= 0:
        return False
    return time.time() >= start_time + settings.timeout


def find_satisfying_template(
    search_strategy, random, condition, tracker, settings, storage=None,
    max_parameter_tries=None,
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
    this a valid test) or NoSuchExample (to indicate that this probably means
    that condition is true with very high probability).

    """
    satisfying_examples = 0
    examples_considered = 0
    timed_out = False
    max_iterations = max(settings.max_iterations, settings.max_examples)
    max_examples = min(max_iterations, settings.max_examples)
    min_satisfying_examples = min(
        settings.min_satisfying_examples,
        max_examples,
    )
    start_time = time.time()

    if storage:
        for example in storage.fetch(search_strategy):
            if examples_considered >= max_iterations:
                break
            examples_considered += 1
            if time_to_call_it_a_day(settings, start_time):
                break
            tracker.track(example)
            try:
                if condition(example):
                    return example
                satisfying_examples += 1
            except UnsatisfiedAssumption:
                pass
            if satisfying_examples >= max_examples:
                break

    parameter_source = ParameterSource(
        random=random, strategy=search_strategy,
        max_tries=max_parameter_tries,
    )

    assert search_strategy.template_upper_bound >= 0
    if isinstance(search_strategy.template_upper_bound, float):
        assert math.isinf(search_strategy.template_upper_bound)
    else:
        assert isinstance(search_strategy.template_upper_bound, int)

    for parameter in parameter_source:  # pragma: no branch
        if len(tracker) >= search_strategy.template_upper_bound:
            break
        if examples_considered >= max_iterations:
            break
        if satisfying_examples >= max_examples:
            break
        if time_to_call_it_a_day(settings, start_time):
            break
        examples_considered += 1

        try:
            example = search_strategy.draw_template(
                random, parameter
            )
        except BadTemplateDraw:
            debug_report(u'Failed attempt to draw a template')
            parameter_source.mark_bad()
            continue
        if tracker.track(example) > 1:
            debug_report(u'Skipping duplicate example')
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
        len(tracker) >= search_strategy.template_upper_bound
    ):
        raise DefinitelyNoSuchExample(
            get_pretty_function_description(condition),
            satisfying_examples,
        )
    elif satisfying_examples < min_satisfying_examples:
        if timed_out:
            raise Timeout((
                u'Ran out of time before finding a satisfying example for '
                u'%s. Only found %d examples (%d satisfying assumptions) in ' +
                u'%.2fs.'
            ) % (
                get_pretty_function_description(condition),
                len(tracker), satisfying_examples, run_time
            ))
        else:
            raise Unsatisfiable((
                u'Unable to satisfy assumptions of hypothesis %s. ' +
                u'Only %d out of %d examples considered satisfied assumptions'
            ) % (
                get_pretty_function_description(condition),
                satisfying_examples, len(tracker)))
    else:
        raise NoSuchExample(get_pretty_function_description(condition))


def simplify_template_such_that(
    search_strategy, random, t, f, tracker, settings, start_time
):
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
    successful_shrinks = 0

    changed = True
    max_warmup = 5
    warmup = 0
    while (
        (changed or warmup < max_warmup) and
        successful_shrinks < settings.max_shrinks
    ):
        changed = False
        warmup += 1
        if warmup < max_warmup:
            debug_report(u'Running warmup simplification round %d' % (
                warmup
            ))
        elif warmup == max_warmup:
            debug_report(u'Warmup is done. Moving on to fully simplifying')

        any_simplifiers = False
        for simplify in search_strategy.simplifiers(random, t):
            debug_report(u'Applying simplification pass %s' % (
                simplify.__name__,
            ))
            any_simplifiers = True
            any_shrinks = False
            while True:
                simpler = simplify(random, t)
                if warmup < max_warmup:
                    simpler = islice(simpler, warmup)
                for s in simpler:
                    any_shrinks = True
                    if time_to_call_it_a_day(settings, start_time):
                        return
                    if tracker.track(s) > 1:
                        debug_report(
                            u'Skipping simplifying to duplicate %s' % (
                                unicode_safe_repr(s),
                            ))
                        continue
                    try:
                        if f(s):
                            successful_shrinks += 1
                            changed = True
                            yield s
                            t = s
                            break
                        else:
                            yield t
                    except UnsatisfiedAssumption:
                        pass
                else:
                    break
            if not any_shrinks:
                debug_report(u'No shrinks possible')
            if successful_shrinks >= settings.max_shrinks:
                break
        if not any_simplifiers:
            debug_report(u'No simplifiers for template %s' % (
                unicode_safe_repr(t),
            ))
            break


def best_satisfying_template(
    search_strategy, random, condition, settings, storage, tracker=None,
    max_parameter_tries=None,
):
    """Find and then minimize a satisfying template.

    First look in storage if it is not None, then attempt to generate
    one. May throw all the exceptions of find_satisfying_template. Once
    an example has been found it will be further minimized.

    """
    if tracker is None:
        tracker = Tracker()
    start_time = time.time()

    successful_shrinks = -1
    with settings:
        satisfying_example = find_satisfying_template(
            search_strategy, random, condition, tracker, settings, storage,
            max_parameter_tries=max_parameter_tries,
        )
        for simpler in simplify_template_such_that(
            search_strategy, random, satisfying_example, condition, tracker,
            settings, start_time,
        ):
            successful_shrinks += 1
            satisfying_example = simpler
        if storage is not None:
            storage.save(satisfying_example, search_strategy)
        if not successful_shrinks:
            verbose_report(u'Could not shrink example')
        elif successful_shrinks == 1:
            verbose_report(u'Successfully shrunk example once')
        else:
            verbose_report(
                u'Successfully shrunk example %d times' % (
                    successful_shrinks,))
        return satisfying_example


def test_is_flaky(test, expected_repr):
    @functools.wraps(test)
    def test_or_flaky(*args, **kwargs):
        text_repr = arg_string(test, args, kwargs)
        if text_repr == expected_repr:
            raise Flaky(
                (
                    u'Hypothesis %s(%s) produces unreliable results: Falsified'
                    u' on the first call but did not on a subsequent one'
                ) % (test.__name__, text_repr,))
        else:
            raise Flaky(
                (
                    u'Hypothesis %s produces unreliable results: Falsified'
                    u' on the first call but did not on a subsequent one.'
                    u' This is possibly due to unreliable values, which may '
                    u'be a bug in the strategy.\nCall 1: %s\nCall 2: %s\n'
                ) % (test.__name__, expected_repr, text_repr,))
    return test_or_flaky


HypothesisProvided = namedtuple(u'HypothesisProvided', (u'value,'))

Example = namedtuple(u'Example', (u'args', u'kwargs'))


def example(*args, **kwargs):
    """Add an explicit example called with these args and kwargs to the
    test."""
    if args and kwargs:
        raise InvalidArgument(
            u'Cannot mix positional and keyword arguments for examples'
        )
    if not (args or kwargs):
        raise InvalidArgument(
            u'An example must provide at least one argument'
        )

    def accept(test):
        if not hasattr(test, u'hypothesis_explicit_examples'):
            test.hypothesis_explicit_examples = []
        test.hypothesis_explicit_examples.append(Example(tuple(args), kwargs))
        return test
    return accept


def reify_and_execute(
    search_strategy, template, test,
    print_example=False, always_print=False, record_repr=None,
):
    def run():
        with BuildContext():
            args, kwargs = search_strategy.reify(template)
            text_version = arg_string(test, args, kwargs)
            if print_example:
                report(
                    lambda: u'Falsifying example: %s(%s)' % (
                        test.__name__, text_version,))
            elif current_verbosity() >= Verbosity.verbose or always_print:
                report(
                    lambda: u'Trying example: %s(%s)' % (
                        test.__name__, text_version))
            if record_repr is not None:
                record_repr[0] = text_version
            return test(*args, **kwargs)
    return run


def given(*generator_arguments, **generator_kwargs):
    """A decorator for turning a test function that accepts arguments into a
    randomized test.

    This is the main entry point to Hypothesis. See the full tutorial
    for details of its behaviour.

    """

    # Keyword only arguments but actually supported in the full range of
    # pythons Hypothesis handles. pop so we don't later pick these up as
    # if they were keyword specifiers for data to pass to the test.
    provided_random = generator_kwargs.pop(u'random', None)
    settings = generator_kwargs.pop(u'settings', None) or Settings.default

    if (provided_random is not None) and settings.derandomize:
        raise InvalidArgument(
            u'Cannot both be derandomized and provide an explicit random')

    if not (generator_arguments or generator_kwargs):
        raise InvalidArgument(
            u'given must be called with at least one argument')

    if generator_arguments and generator_kwargs:
        note_deprecation(
            u'Mixing positional and keyword arguments in a call to given is '
            u'deprecated. Use one or the other.', settings
        )

    def run_test_with_generator(test):
        if settings.derandomize:
            assert provided_random is None
            random = Random(function_digest(test))
        else:
            random = provided_random or Random()

        original_argspec = getargspec(test)
        if generator_arguments and original_argspec.varargs:
            raise InvalidArgument(
                u'varargs are not supported with positional arguments to '
                u'@given'
            )
        extra_kwargs = [
            k for k in generator_kwargs if k not in original_argspec.args]
        if extra_kwargs and not original_argspec.keywords:
            raise InvalidArgument(
                u'%s() got an unexpected keyword argument %r' % (
                    test.__name__,
                    extra_kwargs[0]
                ))
        if (
            len(generator_arguments) > len(original_argspec.args)
        ):
            raise InvalidArgument((
                u'Too many positional arguments for %s() (got %d but'
                u' expected at most %d') % (
                    test.__name__, len(generator_arguments),
                    len(original_argspec.args)))
        arguments = original_argspec.args
        specifiers = list(generator_arguments)
        seen_kwarg = None
        for a in arguments:
            if a in generator_kwargs:
                seen_kwarg = seen_kwarg or a
                specifiers.append(generator_kwargs[a])
            else:
                if seen_kwarg is not None:
                    raise InvalidArgument((
                        u'Argument %s comes after keyword %s which has been '
                        u'specified, but does not itself have a '
                        u'specification') % (
                        a, seen_kwarg
                    ))

        argspec = inspect.ArgSpec(
            args=arguments,
            keywords=original_argspec.keywords,
            varargs=original_argspec.varargs,
            defaults=tuple(map(HypothesisProvided, specifiers))
        )

        unused_kwargs = {}
        for k in extra_kwargs:
            unused_kwargs[k] = HypothesisProvided(generator_kwargs[k])

        @copy_argspec(
            test.__name__, argspec
        )
        def wrapped_test(*arguments, **kwargs):
            selfy = None
            arguments, kwargs = convert_positional_arguments(
                wrapped_test, arguments, kwargs)
            # Anything in unused_kwargs hasn't been injected through
            # argspec.defaults, so we need to add them.
            for k in unused_kwargs:
                if k not in kwargs:
                    kwargs[k] = unused_kwargs[k]
            # If the test function is a method of some kind, the bound object
            # will be the first named argument if there are any, otherwise the
            # first vararg (if any).
            if argspec.args:
                selfy = kwargs.get(argspec.args[0])
            elif arguments:
                selfy = arguments[0]
            if isinstance(selfy, HypothesisProvided):
                selfy = None
            test_runner = executor(selfy)

            for example in getattr(
                wrapped_test, u'hypothesis_explicit_examples', ()
            ):
                if example.args:
                    example_kwargs = dict(zip(
                        argspec.args[-len(example.args):], example.args
                    ))
                else:
                    example_kwargs = dict(example.kwargs)

                for k, v in kwargs.items():
                    if not isinstance(v, HypothesisProvided):
                        example_kwargs[k] = v
                # Note: Test may mutate arguments and we can't rerun explicit
                # examples, so we have to calculate the failure message at this
                # point rather than than later.
                message_on_failure = u'Falsifying example: %s(%s)' % (
                    test.__name__, arg_string(test, arguments, example_kwargs)
                )
                try:
                    test_runner(
                        lambda: test(*arguments, **example_kwargs)
                    )
                except BaseException:
                    report(message_on_failure)
                    raise

            if not any(
                isinstance(x, HypothesisProvided)
                for xs in (arguments, kwargs.values())
                for x in xs
            ):
                # All arguments have been satisfied without needing to invoke
                # hypothesis
                test_runner(lambda: test(*arguments, **kwargs))
                return

            def convert_to_specifier(v):
                if isinstance(v, HypothesisProvided):
                    return strategy(v.value, settings)
                else:
                    return sd.just(v)

            given_specifier = sd.tuples(
                sd.tuples(*map(convert_to_specifier, arguments)),
                sd.fixed_dictionaries(dict(
                    (k, convert_to_specifier(v)) for (k, v) in kwargs.items()))
            )

            search_strategy = strategy(given_specifier, settings)

            if settings.database:
                storage = settings.database.storage(
                    fully_qualified_name(test))
            else:
                storage = None

            last_exception = [None]
            repr_for_last_exception = [None]

            def is_template_example(xs):
                record_repr = [None]
                try:
                    test_runner(reify_and_execute(
                        search_strategy, xs, test,
                        always_print=settings.max_shrinks <= 0,
                        record_repr=record_repr,
                    ))
                    return False
                except UnsatisfiedAssumption as e:
                    raise e
                except Exception as e:
                    if settings.max_shrinks <= 0:
                        raise e
                    last_exception[0] = traceback.format_exc()
                    repr_for_last_exception[0] = record_repr[0]
                    verbose_report(last_exception[0])
                    return True

            is_template_example.__name__ = test.__name__
            is_template_example.__qualname__ = qualname(test)

            falsifying_template = None
            try:
                falsifying_template = best_satisfying_template(
                    search_strategy, random, is_template_example,
                    settings, storage
                )
            except NoSuchExample:
                return

            assert last_exception[0] is not None

            with settings:
                test_runner(reify_and_execute(
                    search_strategy, falsifying_template, test,
                    print_example=True
                ))

                report(
                    u'Failed to reproduce exception. Expected: \n' +
                    last_exception[0],
                )

                test_runner(reify_and_execute(
                    search_strategy, falsifying_template,
                    test_is_flaky(test, repr_for_last_exception[0]),
                    print_example=True
                ))

        wrapped_test.__name__ = test.__name__
        wrapped_test.__doc__ = test.__doc__
        wrapped_test.is_hypothesis_test = True
        wrapped_test.hypothesis_explicit_examples = getattr(
            test, u'hypothesis_explicit_examples', []
        )
        return wrapped_test
    return run_test_with_generator


def find(specifier, condition, settings=None, random=None, storage=None):
    settings = settings or Settings(
        max_examples=2000,
        min_satisfying_examples=0,
        max_shrinks=2000,
    )

    search = strategy(specifier, settings)

    if storage is None and settings.database is not None:
        storage = settings.database.storage(
            u'find(%s)' % (
                binascii.hexlify(function_digest(condition)).decode(u'ascii'),
            )
        )

    random = random or Random()
    successful_examples = [0]

    def template_condition(template):
        with BuildContext():
            result = search.reify(template)
            success = condition(result)

        if success:
            successful_examples[0] += 1

        if not successful_examples[0]:
            verbose_report(lambda: u'Trying example %s' % (
                repr(result),
            ))
        elif success:
            if successful_examples[0] == 1:
                verbose_report(lambda: u'Found satisfying example %s' % (
                    repr(result),
                ))
            else:
                verbose_report(lambda: u'Shrunk example to %s' % (
                    repr(result),
                ))
        return success

    template_condition.__name__ = condition.__name__
    tracker = Tracker()

    try:
        template = best_satisfying_template(
            search, random, template_condition, settings,
            tracker=tracker, max_parameter_tries=2,
            storage=storage,
        )
        with BuildContext():
            return search.reify(template)
    except Timeout:
        raise
    except NoSuchExample:
        if search.template_upper_bound <= len(tracker):
            raise DefinitelyNoSuchExample(
                get_pretty_function_description(condition),
                search.template_upper_bound,
            )
        raise NoSuchExample(get_pretty_function_description(condition))


load_entry_points()
