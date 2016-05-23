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

"""This module provides the core primitives of Hypothesis, assume and given."""


from __future__ import division, print_function, absolute_import

import time
import inspect
import functools
import traceback
from random import Random
from collections import namedtuple

from hypothesis.errors import Flaky, Timeout, NoSuchExample, \
    Unsatisfiable, InvalidArgument, FailedHealthCheck, \
    UnsatisfiedAssumption, HypothesisDeprecationWarning
from hypothesis.control import BuildContext
from hypothesis._settings import settings as Settings
from hypothesis._settings import Phase, Verbosity, HealthCheck
from hypothesis.executors import new_style_executor, \
    default_new_style_executor
from hypothesis.reporting import report, verbose_report, current_verbosity
from hypothesis.internal.compat import getargspec, str_to_bytes
from hypothesis.internal.reflection import nicerepr, arg_string, \
    impersonate, copy_argspec, function_digest, fully_qualified_name, \
    convert_positional_arguments, get_pretty_function_description
from hypothesis.searchstrategy.strategies import SearchStrategy


def new_random():
    import random
    return random.Random(random.getrandbits(128))


def test_is_flaky(test, expected_repr):
    @functools.wraps(test)
    def test_or_flaky(*args, **kwargs):
        text_repr = arg_string(test, args, kwargs)
        raise Flaky(
            (
                'Hypothesis %s(%s) produces unreliable results: Falsified'
                ' on the first call but did not on a subsequent one'
            ) % (test.__name__, text_repr,))
    return test_or_flaky


Example = namedtuple('Example', ('args', 'kwargs'))


def example(*args, **kwargs):
    """Add an explicit example called with these args and kwargs to the
    test."""
    if args and kwargs:
        raise InvalidArgument(
            'Cannot mix positional and keyword arguments for examples'
        )
    if not (args or kwargs):
        raise InvalidArgument(
            'An example must provide at least one argument'
        )

    def accept(test):
        if not hasattr(test, 'hypothesis_explicit_examples'):
            test.hypothesis_explicit_examples = []
        test.hypothesis_explicit_examples.append(Example(tuple(args), kwargs))
        return test
    return accept


def reify_and_execute(
    search_strategy, test,
    print_example=False,
    is_final=False,
):
    from hypothesis.strategies import random_module

    def run(data):
        from hypothesis.control import note

        with BuildContext(is_final=is_final):
            seed = data.draw(random_module()).seed
            if seed != 0:
                note('random.seed(%d)' % (seed,))
            args, kwargs = data.draw(search_strategy)

            if print_example:
                report(
                    lambda: 'Falsifying example: %s(%s)' % (
                        test.__name__, arg_string(test, args, kwargs)))
            elif current_verbosity() >= Verbosity.verbose:
                report(
                    lambda: 'Trying example: %s(%s)' % (
                        test.__name__, arg_string(test, args, kwargs)))
            return test(*args, **kwargs)
    return run


def seed(seed):
    """
    seed: Start the test execution from a specific seed. May be any hashable
          object. No exact meaning for seed is provided other than that
          for a fixed seed value Hypothesis will try the same actions (insofar
          as it can given external sources of non-determinism. e.g. timing and
          hash randomization).
          Overrides the derandomize setting if it is present.
    """

    def accept(test):
        test._hypothesis_internal_use_seed = seed
        return test
    return accept


class WithRunner(SearchStrategy):

    def __init__(self, base, runner):
        assert runner is not None
        self.base = base
        self.runner = runner

    def do_draw(self, data):
        data.hypothesis_runner = self.runner
        return self.base.do_draw(data)


def given(*generator_arguments, **generator_kwargs):
    """A decorator for turning a test function that accepts arguments into a
    randomized test.

    This is the main entry point to Hypothesis. See the full tutorial
    for details of its behaviour.

    """
    def run_test_with_generator(test):
        original_argspec = getargspec(test)

        def invalid(message):
            def wrapped_test(*arguments, **kwargs):
                raise InvalidArgument(message)
            return wrapped_test

        if not (generator_arguments or generator_kwargs):
            return invalid(
                'given must be called with at least one argument')

        if (
            generator_arguments and (
                original_argspec.varargs or original_argspec.keywords)
        ):
            return invalid(
                'varargs or keywords are not supported with positional '
                'arguments to @given'
            )

        if (
            len(generator_arguments) > len(original_argspec.args)
        ):
            return invalid((
                'Too many positional arguments for %s() (got %d but'
                ' expected at most %d') % (
                    test.__name__, len(generator_arguments),
                    len(original_argspec.args)))

        if generator_arguments and generator_kwargs:
            return invalid(
                'cannot mix positional and keyword arguments to @given'
            )
        extra_kwargs = [
            k for k in generator_kwargs if k not in original_argspec.args]
        if extra_kwargs and not original_argspec.keywords:
            return invalid(
                '%s() got an unexpected keyword argument %r' % (
                    test.__name__,
                    extra_kwargs[0]
                ))
        arguments = original_argspec.args
        for a in arguments:
            if isinstance(a, list):  # pragma: no cover
                return invalid((
                    'Cannot decorate function %s() because it has '
                    'destructuring arguments') % (
                        test.__name__,
                ))
        if original_argspec.defaults:
            return invalid(
                'Cannot apply @given to a function with defaults.'
            )
        for name, strategy in zip(
            arguments[-len(generator_arguments):], generator_arguments
        ):
            generator_kwargs[name] = strategy

        argspec = inspect.ArgSpec(
            args=[a for a in arguments if a not in generator_kwargs],
            keywords=original_argspec.keywords,
            varargs=original_argspec.varargs,
            defaults=None
        )

        @impersonate(test)
        @copy_argspec(
            test.__name__, argspec
        )
        def wrapped_test(*arguments, **kwargs):
            settings = wrapped_test._hypothesis_internal_use_settings
            if wrapped_test._hypothesis_internal_use_seed is not None:
                random = Random(
                    wrapped_test._hypothesis_internal_use_seed)
            elif settings.derandomize:
                random = Random(function_digest(test))
            else:
                random = new_random()

            import hypothesis.strategies as sd

            selfy = None
            arguments, kwargs = convert_positional_arguments(
                wrapped_test, arguments, kwargs)

            # If the test function is a method of some kind, the bound object
            # will be the first named argument if there are any, otherwise the
            # first vararg (if any).
            if argspec.args:
                selfy = kwargs.get(argspec.args[0])
            elif arguments:
                selfy = arguments[0]
            test_runner = new_style_executor(selfy)

            for example in reversed(getattr(
                wrapped_test, 'hypothesis_explicit_examples', ()
            )):
                if example.args:
                    if len(example.args) > len(original_argspec.args):
                        raise InvalidArgument(
                            'example has too many arguments for test. '
                            'Expected at most %d but got %d' % (
                                len(original_argspec.args), len(example.args)))
                    example_kwargs = dict(zip(
                        original_argspec.args[-len(example.args):],
                        example.args
                    ))
                else:
                    example_kwargs = example.kwargs
                if Phase.explicit not in settings.phases:
                    continue
                example_kwargs.update(kwargs)
                # Note: Test may mutate arguments and we can't rerun explicit
                # examples, so we have to calculate the failure message at this
                # point rather than than later.
                message_on_failure = 'Falsifying example: %s(%s)' % (
                    test.__name__, arg_string(test, arguments, example_kwargs)
                )
                try:
                    with BuildContext() as b:
                        test_runner(
                            None,
                            lambda data: test(*arguments, **example_kwargs)
                        )
                except BaseException:
                    report(message_on_failure)
                    for n in b.notes:
                        report(n)
                    raise
            if settings.max_examples <= 0:
                return

            arguments = tuple(arguments)

            given_specifier = sd.tuples(
                sd.just(arguments),
                sd.fixed_dictionaries(generator_kwargs).map(
                    lambda args: dict(args, **kwargs)
                )
            )

            def fail_health_check(message, label):
                if label in settings.suppress_health_check:
                    return
                message += (
                    '\nSee http://hypothesis.readthedocs.org/en/latest/health'
                    'checks.html for more information about this. '
                )
                message += (
                    'If you want to disable just this health check, add %s '
                    'to the suppress_health_check settings for this test.'
                ) % (label,)
                raise FailedHealthCheck(message)

            search_strategy = given_specifier
            if selfy is not None:
                search_strategy = WithRunner(search_strategy, selfy)

            search_strategy.validate()

            perform_health_check = settings.perform_health_check
            perform_health_check &= Settings.default.perform_health_check

            from hypothesis.internal.conjecture.data import TestData, Status, \
                StopTest
            if not (
                Phase.reuse in settings.phases or
                Phase.generate in settings.phases
            ):
                return

            if perform_health_check:
                health_check_random = Random(random.getrandbits(128))
                # We "pre warm" the health check with one draw to give it some
                # time to calculate any cached data. This prevents the case
                # where the first draw of the health check takes ages because
                # of loading unicode data the first time.
                data = TestData(
                    max_length=settings.buffer_size,
                    draw_bytes=lambda data, n, distribution:
                    distribution(health_check_random, n)
                )
                with Settings(settings, verbosity=Verbosity.quiet):
                    try:
                        test_runner(data, reify_and_execute(
                            search_strategy,
                            lambda *args, **kwargs: None,
                        ))
                    except BaseException:
                        pass
                count = 0
                overruns = 0
                filtered_draws = 0
                start = time.time()
                while (
                    count < 10 and time.time() < start + 1 and
                    filtered_draws < 50 and overruns < 20
                ):
                    try:
                        data = TestData(
                            max_length=settings.buffer_size,
                            draw_bytes=lambda data, n, distribution:
                            distribution(health_check_random, n)
                        )
                        with Settings(settings, verbosity=Verbosity.quiet):
                            test_runner(data, reify_and_execute(
                                search_strategy,
                                lambda *args, **kwargs: None,
                            ))
                        count += 1
                    except UnsatisfiedAssumption:
                        filtered_draws += 1
                    except StopTest:
                        if data.status == Status.INVALID:
                            filtered_draws += 1
                        else:
                            assert data.status == Status.OVERRUN
                            overruns += 1
                    except InvalidArgument:
                        raise
                    except Exception:
                        if (
                            HealthCheck.exception_in_generation in
                            settings.suppress_health_check
                        ):
                            raise
                        report(traceback.format_exc())
                        if test_runner is default_new_style_executor:
                            fail_health_check(
                                'An exception occurred during data '
                                'generation in initial health check. '
                                'This indicates a bug in the strategy. '
                                'This could either be a Hypothesis bug or '
                                "an error in a function you've passed to "
                                'it to construct your data.',
                                HealthCheck.exception_in_generation,
                            )
                        else:
                            fail_health_check(
                                'An exception occurred during data '
                                'generation in initial health check. '
                                'This indicates a bug in the strategy. '
                                'This could either be a Hypothesis bug or '
                                'an error in a function you\'ve passed to '
                                'it to construct your data. Additionally, '
                                'you have a custom executor, which means '
                                'that this could be your executor failing '
                                'to handle a function which returns None. ',
                                HealthCheck.exception_in_generation,
                            )
                if overruns >= 20 or (
                    not count and overruns > 0
                ):
                    fail_health_check((
                        'Examples routinely exceeded the max allowable size. '
                        '(%d examples overran while generating %d valid ones)'
                        '. Generating examples this large will usually lead to'
                        ' bad results. You should try setting average_size or '
                        'max_size parameters on your collections and turning '
                        'max_leaves down on recursive() calls.') % (
                        overruns, count
                    ), HealthCheck.data_too_large)
                if filtered_draws >= 50 or (
                    not count and filtered_draws > 0
                ):
                    fail_health_check((
                        'It looks like your strategy is filtering out a lot '
                        'of data. Health check found %d filtered examples but '
                        'only %d good ones. This will make your tests much '
                        'slower, and also will probably distort the data '
                        'generation quite a lot. You should adapt your '
                        'strategy to filter less. This can also be caused by '
                        'a low max_leaves parameter in recursive() calls') % (
                        filtered_draws, count
                    ), HealthCheck.filter_too_much)
                runtime = time.time() - start
                if runtime > 1.0 or count < 10:
                    fail_health_check((
                        'Data generation is extremely slow: Only produced '
                        '%d valid examples in %.2f seconds (%d invalid ones '
                        'and %d exceeded maximum size). Try decreasing '
                        "size of the data you're generating (with e.g."
                        'average_size or max_leaves parameters).'
                    ) % (count, runtime, filtered_draws, overruns),
                        HealthCheck.too_slow,
                    )
            last_exception = [None]
            repr_for_last_exception = [None]

            def evaluate_test_data(data):
                try:
                    result = test_runner(data, reify_and_execute(
                        search_strategy, test,
                    ))
                    if result is not None and settings.perform_health_check:
                        fail_health_check((
                            'Tests run under @given should return None, but '
                            '%s returned %r instead.'
                        ) % (test.__name__, result), HealthCheck.return_value)
                    return False
                except UnsatisfiedAssumption:
                    data.mark_invalid()
                except (
                    HypothesisDeprecationWarning, FailedHealthCheck,
                    StopTest,
                ):
                    raise
                except Exception:
                    last_exception[0] = traceback.format_exc()
                    verbose_report(last_exception[0])
                    data.mark_interesting()

            from hypothesis.internal.conjecture.engine import TestRunner

            falsifying_example = None
            database_key = str_to_bytes(fully_qualified_name(test))
            start_time = time.time()
            runner = TestRunner(
                evaluate_test_data,
                settings=settings, random=random,
                database_key=database_key,
            )
            runner.run()
            run_time = time.time() - start_time
            timed_out = (
                settings.timeout > 0 and
                run_time >= settings.timeout
            )
            if runner.last_data is None:
                return
            if runner.last_data.status == Status.INTERESTING:
                falsifying_example = runner.last_data.buffer
                if settings.database is not None:
                    settings.database.save(
                        database_key, falsifying_example
                    )
            else:
                if runner.valid_examples < min(
                    settings.min_satisfying_examples,
                    settings.max_examples,
                ):
                    if timed_out:
                        raise Timeout((
                            'Ran out of time before finding a satisfying '
                            'example for '
                            '%s. Only found %d examples in ' +
                            '%.2fs.'
                        ) % (
                            get_pretty_function_description(test),
                            runner.valid_examples, run_time
                        ))
                    else:
                        raise Unsatisfiable((
                            'Unable to satisfy assumptions of hypothesis '
                            '%s. Only %d examples considered '
                            'satisfied assumptions'
                        ) % (
                            get_pretty_function_description(test),
                            runner.valid_examples,))
                return

            assert last_exception[0] is not None

            try:
                with settings:
                    test_runner(
                        TestData.for_buffer(falsifying_example),
                        reify_and_execute(
                            search_strategy, test,
                            print_example=True, is_final=True
                        ))
            except (UnsatisfiedAssumption, StopTest):
                report(traceback.format_exc())
                raise Flaky(
                    'Unreliable assumption: An example which satisfied '
                    'assumptions on the first run now fails it.'
                )

            report(
                'Failed to reproduce exception. Expected: \n' +
                last_exception[0],
            )

            filter_message = (
                'Unreliable test data: Failed to reproduce a failure '
                'and then when it came to recreating the example in '
                'order to print the test data with a flaky result '
                'the example was filtered out (by e.g. a '
                'call to filter in your strategy) when we didn\'t '
                'expect it to be.'
            )

            try:
                test_runner(
                    TestData.for_buffer(falsifying_example),
                    reify_and_execute(
                        search_strategy,
                        test_is_flaky(test, repr_for_last_exception[0]),
                        print_example=True, is_final=True
                    ))
            except (UnsatisfiedAssumption, StopTest):
                raise Flaky(filter_message)
        for attr in dir(test):
            if attr[0] != '_' and not hasattr(wrapped_test, attr):
                setattr(wrapped_test, attr, getattr(test, attr))
        wrapped_test.is_hypothesis_test = True
        wrapped_test._hypothesis_internal_use_seed = getattr(
            test, '_hypothesis_internal_use_seed', None
        )
        wrapped_test._hypothesis_internal_use_settings = getattr(
            test, '_hypothesis_internal_use_settings', None
        ) or Settings.default
        return wrapped_test
    return run_test_with_generator


def find(specifier, condition, settings=None, random=None, database_key=None):
    settings = settings or Settings(
        max_examples=2000,
        min_satisfying_examples=0,
        max_shrinks=2000,
    )

    if database_key is None and settings.database is not None:
        database_key = function_digest(condition)

    if not isinstance(specifier, SearchStrategy):
        raise InvalidArgument(
            'Expected SearchStrategy but got %r of type %s' % (
                specifier, type(specifier).__name__
            ))

    search = specifier

    random = random or new_random()
    successful_examples = [0]
    last_data = [None]

    def template_condition(data):
        with BuildContext():
            try:
                data.is_find = True
                result = data.draw(search)
                data.note(result)
                success = condition(result)
            except UnsatisfiedAssumption:
                data.mark_invalid()

        if success:
            successful_examples[0] += 1

        if settings.verbosity == Verbosity.verbose:
            if not successful_examples[0]:
                report(lambda: u'Trying example %s' % (
                    nicerepr(result),
                ))
            elif success:
                if successful_examples[0] == 1:
                    report(lambda: u'Found satisfying example %s' % (
                        nicerepr(result),
                    ))
                else:
                    report(lambda: u'Shrunk example to %s' % (
                        nicerepr(result),
                    ))
                last_data[0] = data
        if success and not data.frozen:
            data.mark_interesting()
    from hypothesis.internal.conjecture.engine import TestRunner
    from hypothesis.internal.conjecture.data import TestData, Status

    start = time.time()
    runner = TestRunner(
        template_condition, settings=settings, random=random,
        database_key=database_key,
    )
    runner.run()
    run_time = time.time() - start
    if runner.last_data.status == Status.INTERESTING:
        with BuildContext():
            return TestData.for_buffer(runner.last_data.buffer).draw(search)
    if runner.valid_examples <= settings.min_satisfying_examples:
        if settings.timeout > 0 and run_time > settings.timeout:
            raise Timeout((
                'Ran out of time before finding enough valid examples for '
                '%s. Only %d valid examples found in %.2f seconds.'
            ) % (
                get_pretty_function_description(condition),
                runner.valid_examples, run_time))

        else:
            raise Unsatisfiable((
                'Unable to satisfy assumptions of '
                '%s. Only %d examples considered satisfied assumptions'
            ) % (
                get_pretty_function_description(condition),
                runner.valid_examples,))

    raise NoSuchExample(get_pretty_function_description(condition))
