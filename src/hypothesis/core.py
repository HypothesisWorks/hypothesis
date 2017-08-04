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

"""This module provides the core primitives of Hypothesis, such as given."""


from __future__ import division, print_function, absolute_import

import time
import functools
import traceback
from random import Random
from collections import namedtuple

import hypothesis.strategies as st
from hypothesis.errors import Flaky, Timeout, NoSuchExample, \
    Unsatisfiable, InvalidArgument, FailedHealthCheck, \
    UnsatisfiedAssumption, HypothesisDeprecationWarning
from hypothesis.control import BuildContext
from hypothesis._settings import settings as Settings
from hypothesis._settings import Phase, Verbosity, HealthCheck, \
    note_deprecation
from hypothesis.executors import new_style_executor, \
    default_new_style_executor
from hypothesis.reporting import report, verbose_report, current_verbosity
from hypothesis.statistics import note_engine_for_statistics
from hypothesis.internal.compat import str_to_bytes, get_type_hints, \
    getfullargspec
from hypothesis.utils.conventions import infer
from hypothesis.internal.escalation import \
    escalate_hypothesis_internal_error
from hypothesis.internal.reflection import nicerepr, arg_string, \
    impersonate, function_digest, fully_qualified_name, \
    define_function_signature, convert_positional_arguments, \
    get_pretty_function_description
from hypothesis.internal.conjecture.data import Status, StopTest, \
    ConjectureData
from hypothesis.searchstrategy.strategies import SearchStrategy
from hypothesis.internal.conjecture.engine import ExitReason, \
    ConjectureRunner


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
    """A decorator to that ensures a specific example is always tested."""
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
    def run(data):
        with BuildContext(data, is_final=is_final):
            import random as rnd_module
            rnd_module.seed(0)
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
    """seed: Start the test execution from a specific seed.

    May be any hashable object. No exact meaning for seed is provided
    other than that for a fixed seed value Hypothesis will try the same
    actions (insofar as it can given external sources of non-
    determinism. e.g. timing and hash randomization). Overrides the
    derandomize setting if it is present.

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


def is_invalid_test(
    name, original_argspec, generator_arguments, generator_kwargs
):
    def invalid(message):
        def wrapped_test(*arguments, **kwargs):
            raise InvalidArgument(message)
        return wrapped_test

    if not (generator_arguments or generator_kwargs):
        return invalid(
            'given must be called with at least one argument')

    if generator_arguments and any([original_argspec.varargs,
                                    original_argspec.varkw,
                                    original_argspec.kwonlyargs]):
        return invalid(
            'positional arguments to @given are not supported with varargs, '
            'varkeywords, or keyword-only arguments'
        )

    if len(generator_arguments) > len(original_argspec.args):
        return invalid((
            'Too many positional arguments for %s() (got %d but'
            ' expected at most %d') % (
                name, len(generator_arguments),
                len(original_argspec.args)))

    if infer in generator_arguments:
        return invalid('infer was passed as a positional argument to @given, '
                       'but may only be passed as a keyword argument')

    if generator_arguments and generator_kwargs:
        return invalid(
            'cannot mix positional and keyword arguments to @given'
        )
    extra_kwargs = [
        k for k in generator_kwargs
        if k not in original_argspec.args + original_argspec.kwonlyargs
    ]
    if extra_kwargs and not original_argspec.varkw:
        return invalid(
            '%s() got an unexpected keyword argument %r' % (
                name,
                extra_kwargs[0]
            ))
    for a in original_argspec.args:
        if isinstance(a, list):  # pragma: no cover
            return invalid((
                'Cannot decorate function %s() because it has '
                'destructuring arguments') % (
                    name,
            ))
    if original_argspec.defaults or original_argspec.kwonlydefaults:
        return invalid('Cannot apply @given to a function with defaults.')
    missing = [repr(kw) for kw in original_argspec.kwonlyargs
               if kw not in generator_kwargs]
    if missing:
        raise InvalidArgument('Missing required kwarg{}: {}'.format(
            's' if len(missing) > 1 else '', ', '.join(missing)))


def execute_explicit_examples(
    test_runner, test, wrapped_test, settings, arguments, kwargs
):
    original_argspec = getfullargspec(test)

    for example in reversed(getattr(
        wrapped_test, 'hypothesis_explicit_examples', ()
    )):
        example_kwargs = dict(original_argspec.kwonlydefaults or {})
        if example.args:
            if len(example.args) > len(original_argspec.args):
                raise InvalidArgument(
                    'example has too many arguments for test. '
                    'Expected at most %d but got %d' % (
                        len(original_argspec.args), len(example.args)))
            example_kwargs.update(dict(zip(
                original_argspec.args[-len(example.args):],
                example.args
            )))
        else:
            example_kwargs.update(example.kwargs)
        if Phase.explicit not in settings.phases:
            continue
        example_kwargs.update(kwargs)
        # Note: Test may mutate arguments and we can't rerun explicit
        # examples, so we have to calculate the failure message at this
        # point rather than than later.
        example_string = '%s(%s)' % (
            test.__name__, arg_string(test, arguments, example_kwargs)
        )
        try:
            with BuildContext(None) as b:
                if settings.verbosity >= Verbosity.verbose:
                    report('Trying example: ' + example_string)
                test_runner(
                    None,
                    lambda data: test(*arguments, **example_kwargs)
                )
        except BaseException:
            traceback.print_exc()
            report('Falsifying example: ' + example_string)
            for n in b.notes:
                report(n)
            raise


def fail_health_check(settings, message, label):
    # Tell pytest to omit the body of this function from tracebacks
    # http://doc.pytest.org/en/latest/example/simple.html#writing-well-integrated-assertion-helpers
    __tracebackhide__ = True

    if label in settings.suppress_health_check:
        return
    if not settings.perform_health_check:
        return
    message += (
        '\nSee https://hypothesis.readthedocs.io/en/latest/health'
        'checks.html for more information about this. '
    )
    message += (
        'If you want to disable just this health check, add %s '
        'to the suppress_health_check settings for this test.'
    ) % (label,)
    raise FailedHealthCheck(message)


def perform_health_checks(random, settings, test_runner, search_strategy):
    # Tell pytest to omit the body of this function from tracebacks
    __tracebackhide__ = True
    if not settings.perform_health_check:
        return
    if not Settings.default.perform_health_check:
        return

    health_check_random = Random(random.getrandbits(128))
    # We "pre warm" the health check with one draw to give it some
    # time to calculate any cached data. This prevents the case
    # where the first draw of the health check takes ages because
    # of loading unicode data the first time.
    data = ConjectureData(
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
            data = ConjectureData(
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
            escalate_hypothesis_internal_error()
            if (
                HealthCheck.exception_in_generation in
                settings.suppress_health_check
            ):
                raise
            report(traceback.format_exc())
            if test_runner is default_new_style_executor:
                fail_health_check(
                    settings,
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
                    settings,
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
        fail_health_check(settings, (
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
        fail_health_check(settings, (
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
        fail_health_check(settings, (
            'Data generation is extremely slow: Only produced '
            '%d valid examples in %.2f seconds (%d invalid ones '
            'and %d exceeded maximum size). Try decreasing '
            "size of the data you're generating (with e.g."
            'average_size or max_leaves parameters).'
        ) % (count, runtime, filtered_draws, overruns),
            HealthCheck.too_slow,
        )


def get_random_for_wrapped_test(test, wrapped_test):
    settings = wrapped_test._hypothesis_internal_use_settings

    if wrapped_test._hypothesis_internal_use_seed is not None:
        return Random(
            wrapped_test._hypothesis_internal_use_seed)
    elif settings.derandomize:
        return Random(function_digest(test))
    else:
        return new_random()


def process_arguments_to_given(
    wrapped_test, arguments, kwargs, generator_arguments, generator_kwargs,
    argspec, test, settings
):
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

    arguments = tuple(arguments)

    search_strategy = st.tuples(
        st.just(arguments),
        st.fixed_dictionaries(generator_kwargs).map(
            lambda args: dict(args, **kwargs)
        )
    )

    if selfy is not None:
        search_strategy = WithRunner(search_strategy, selfy)

    search_strategy.validate()

    return arguments, kwargs, test_runner, search_strategy


def skip_exceptions_to_reraise():
    """Return a tuple of exceptions meaning 'skip this test', to re-raise.

    This is intended to cover most common test runners; if you would
    like another to be added please open an issue or pull request.

    """
    import unittest
    # This is a set because nose may simply re-export unittest.SkipTest
    exceptions = set([unittest.SkipTest])

    try:  # pragma: no cover
        from unittest2 import SkipTest
        exceptions.add(SkipTest)
    except ImportError:
        pass

    try:  # pragma: no cover
        from pytest.runner import Skipped
        exceptions.add(Skipped)
    except ImportError:
        pass

    try:  # pragma: no cover
        from nose import SkipTest as NoseSkipTest
        exceptions.add(NoseSkipTest)
    except ImportError:
        pass

    return tuple(sorted(exceptions, key=str))


exceptions_to_reraise = skip_exceptions_to_reraise()


def new_given_argspec(original_argspec, generator_kwargs):
    """Make an updated argspec for the wrapped test."""
    new_args = [a for a in original_argspec.args if a not in generator_kwargs]
    new_kwonlyargs = [a for a in original_argspec.kwonlyargs
                      if a not in generator_kwargs]
    annots = {k: v for k, v in original_argspec.annotations.items()
              if k in new_args + new_kwonlyargs}
    annots['return'] = None
    return original_argspec._replace(
        args=new_args, kwonlyargs=new_kwonlyargs, annotations=annots)


HUNG_TEST_TIME_LIMIT = 5 * 60


class StateForActualGivenExecution(object):

    def __init__(self, test_runner, search_strategy, test, settings, random):
        self.test_runner = test_runner
        self.search_strategy = search_strategy
        self.test = test
        self.settings = settings
        self.at_least_one_success = False
        self.last_exception = None
        self.repr_for_last_exception = None
        self.falsifying_example = None
        self.random = random

    def evaluate_test_data(self, data):
        if (
            time.time() - self.start_time >= HUNG_TEST_TIME_LIMIT
        ):
            fail_health_check(self.settings, (
                'Your test has been running for at least five minutes. This '
                'is probably not what you intended, so by default Hypothesis '
                'turns it into an error.'
            ), HealthCheck.hung_test)

        try:
            result = self.test_runner(data, reify_and_execute(
                self.search_strategy, self.test,
            ))
            if result is not None and self.settings.perform_health_check:
                fail_health_check(self.settings, (
                    'Tests run under @given should return None, but '
                    '%s returned %r instead.'
                ) % (self.test.__name__, result), HealthCheck.return_value)
            self.at_least_one_success = True
            return False
        except UnsatisfiedAssumption:
            data.mark_invalid()
        except (
            HypothesisDeprecationWarning, FailedHealthCheck,
            StopTest,
        ) + exceptions_to_reraise:
            raise
        except Exception:
            escalate_hypothesis_internal_error()
            self.last_exception = traceback.format_exc()
            verbose_report(self.last_exception)
            data.mark_interesting()

    def run(self):
        # Tell pytest to omit the body of this function from tracebacks
        __tracebackhide__ = True
        database_key = str_to_bytes(fully_qualified_name(self.test))
        self.start_time = time.time()
        runner = ConjectureRunner(
            self.evaluate_test_data,
            settings=self.settings, random=self.random,
            database_key=database_key,
        )
        runner.run()
        note_engine_for_statistics(runner)
        run_time = time.time() - self.start_time
        timed_out = runner.exit_reason == ExitReason.timeout
        if runner.last_data is None:
            return
        if runner.last_data.status == Status.INTERESTING:
            self.falsifying_example = runner.last_data.buffer
            if self.settings.database is not None:
                self.settings.database.save(
                    database_key, self.falsifying_example
                )
        else:
            if timed_out:
                note_deprecation((
                    'Your tests are hitting the settings timeout (%.2fs). '
                    'This functionality will go away in a future release '
                    'and you should not rely on it. Instead, try setting '
                    'max_examples to be some value lower than %d (the number '
                    'of examples your test successfully ran here). Or, if you '
                    'would prefer your tests to run to completion, regardless '
                    'of how long they take, you can set the timeout value to '
                    'hypothesis.unlimited.'
                ) % (
                    self.settings.timeout, runner.valid_examples),
                    self.settings)
            if runner.valid_examples < min(
                self.settings.min_satisfying_examples,
                self.settings.max_examples,
            ) and not (
                runner.exit_reason == ExitReason.finished and
                self.at_least_one_success
            ):
                if timed_out:
                    raise Timeout((
                        'Ran out of time before finding a satisfying '
                        'example for '
                        '%s. Only found %d examples in ' +
                        '%.2fs.'
                    ) % (
                        get_pretty_function_description(self.test),
                        runner.valid_examples, run_time
                    ))
                else:
                    raise Unsatisfiable((
                        'Unable to satisfy assumptions of hypothesis '
                        '%s. Only %d examples considered '
                        'satisfied assumptions'
                    ) % (
                        get_pretty_function_description(self.test),
                        runner.valid_examples,))

        if self.falsifying_example is None:
            return

        assert self.last_exception is not None

        try:
            with self.settings:
                self.test_runner(
                    ConjectureData.for_buffer(self.falsifying_example),
                    reify_and_execute(
                        self.search_strategy, self.test,
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
            self.last_exception,
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
            self.test_runner(
                ConjectureData.for_buffer(self.falsifying_example),
                reify_and_execute(
                    self.search_strategy,
                    test_is_flaky(self.test, self.repr_for_last_exception),
                    print_example=True, is_final=True
                ))
        except (UnsatisfiedAssumption, StopTest):
            raise Flaky(filter_message)


def given(*given_arguments, **given_kwargs):
    """A decorator for turning a test function that accepts arguments into a
    randomized test.

    This is the main entry point to Hypothesis.

    """
    def run_test_with_generator(test):
        generator_arguments = tuple(given_arguments)
        generator_kwargs = dict(given_kwargs)

        original_argspec = getfullargspec(test)

        check_invalid = is_invalid_test(
            test.__name__, original_argspec,
            generator_arguments, generator_kwargs)

        if check_invalid is not None:
            return check_invalid

        for name, strategy in zip(reversed(original_argspec.args),
                                  reversed(generator_arguments)):
            generator_kwargs[name] = strategy

        argspec = new_given_argspec(original_argspec, generator_kwargs)

        @impersonate(test)
        @define_function_signature(
            test.__name__, test.__doc__, argspec
        )
        def wrapped_test(*arguments, **kwargs):
            # Tell pytest to omit the body of this function from tracebacks
            __tracebackhide__ = True

            settings = wrapped_test._hypothesis_internal_use_settings

            random = get_random_for_wrapped_test(test, wrapped_test)

            if infer in generator_kwargs.values():
                hints = get_type_hints(test)
            for name in [name for name, value in generator_kwargs.items()
                         if value is infer]:
                if name not in hints:
                    raise InvalidArgument(
                        'passed %s=infer for %s, but %s has no type annotation'
                        % (name, test.__name__, name))
                generator_kwargs[name] = st.from_type(hints[name])

            processed_args = process_arguments_to_given(
                wrapped_test, arguments, kwargs, generator_arguments,
                generator_kwargs, argspec, test, settings
            )
            arguments, kwargs, test_runner, search_strategy = processed_args

            execute_explicit_examples(
                test_runner, test, wrapped_test, settings, arguments, kwargs
            )

            if settings.max_examples <= 0:
                return

            if not (
                Phase.reuse in settings.phases or
                Phase.generate in settings.phases
            ):
                return

            perform_health_checks(
                random, settings, test_runner, search_strategy)

            state = StateForActualGivenExecution(
                test_runner, search_strategy, test, settings, random)
            state.run()

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
    """Returns the minimal example from the given strategy ``specifier`` that
    matches the predicate function ``condition``."""
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
    specifier.validate()

    search = specifier

    random = random or new_random()
    successful_examples = [0]
    last_data = [None]

    def template_condition(data):
        with BuildContext(data):
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
    start = time.time()
    runner = ConjectureRunner(
        template_condition, settings=settings, random=random,
        database_key=database_key,
    )
    runner.run()
    note_engine_for_statistics(runner)
    run_time = time.time() - start
    if runner.last_data.status == Status.INTERESTING:
        data = ConjectureData.for_buffer(runner.last_data.buffer)
        with BuildContext(data):
            return data.draw(search)
    if (
        runner.valid_examples <= settings.min_satisfying_examples and
        runner.exit_reason != ExitReason.finished
    ):
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
