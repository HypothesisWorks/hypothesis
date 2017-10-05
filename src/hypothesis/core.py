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

import os
import sys
import time
import functools
import traceback
from random import Random

import attr
from coverage import CoverageData
from coverage.files import canonical_filename
from coverage.collector import Collector

import hypothesis.strategies as st
from hypothesis.errors import Flaky, Timeout, NoSuchExample, \
    Unsatisfiable, InvalidArgument, DeadlineExceeded, MultipleFailures, \
    FailedHealthCheck, UnsatisfiedAssumption, \
    HypothesisDeprecationWarning
from hypothesis.control import BuildContext
from hypothesis._settings import settings as Settings
from hypothesis._settings import Phase, Verbosity, HealthCheck, \
    note_deprecation
from hypothesis.executors import new_style_executor, \
    default_new_style_executor
from hypothesis.reporting import report, verbose_report, current_verbosity
from hypothesis.statistics import note_engine_for_statistics
from hypothesis.internal.compat import ceil, str_to_bytes, \
    get_type_hints, getfullargspec, encoded_filepath
from hypothesis.internal.coverage import IN_COVERAGE_TESTS
from hypothesis.utils.conventions import infer, not_set
from hypothesis.internal.escalation import is_hypothesis_file, \
    escalate_hypothesis_internal_error
from hypothesis.internal.reflection import is_mock, proxies, nicerepr, \
    arg_string, impersonate, function_digest, fully_qualified_name, \
    define_function_signature, convert_positional_arguments, \
    get_pretty_function_description
from hypothesis.internal.conjecture.data import Status, StopTest, \
    ConjectureData
from hypothesis.searchstrategy.strategies import SearchStrategy
from hypothesis.internal.conjecture.engine import ExitReason, \
    ConjectureRunner, uniform, sort_key

try:
    from coverage.tracer import CFileDisposition as FileDisposition
except ImportError:  # pragma: no cover
    from coverage.collector import FileDisposition


running_under_pytest = False
global_force_seed = None


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


@attr.s()
class Example(object):
    args = attr.ib()
    kwargs = attr.ib()


def example(*args, **kwargs):
    """A decorator which ensures a specific example is always tested."""
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
    is_final=False, collector=None
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
            if collector is None:
                return test(*args, **kwargs)
            else:  # pragma: no cover
                try:
                    collector.start()
                    return test(*args, **kwargs)
                finally:
                    collector.stop()

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
        draw_bytes=lambda data, n: uniform(health_check_random, n)
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
                draw_bytes=lambda data, n: uniform(health_check_random, n)
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
    wrapped_test._hypothesis_internal_use_generated_seed = None

    if wrapped_test._hypothesis_internal_use_seed is not None:
        return Random(
            wrapped_test._hypothesis_internal_use_seed)
    elif settings.derandomize:
        return Random(function_digest(test))
    elif global_force_seed is not None:
        return Random(global_force_seed)
    else:
        import random
        seed = random.getrandbits(128)
        wrapped_test._hypothesis_internal_use_generated_seed = seed
        return Random(seed)


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

    # Ensure that we don't mistake mocks for self here.
    # This can cause the mock to be used as the test runner.
    if is_mock(selfy):
        selfy = None

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


ROOT = os.path.dirname(__file__)

STDLIB = os.path.dirname(os.__file__)


def hypothesis_check_include(filename):  # pragma: no cover
    if is_hypothesis_file(filename):
        return False
    return filename.endswith('.py')


def escalate_warning(msg, slug=None):  # pragma: no cover
    if slug is not None:
        msg = '%s (%s)' % (msg, slug)
    raise AssertionError(
        'Unexpected warning from coverage: %s' % (msg,)
    )


@attr.s(slots=True, frozen=True)
class Arc(object):
    filename = attr.ib()
    source = attr.ib()
    target = attr.ib()


in_given = False

FORCE_PURE_TRACER = os.getenv('HYPOTHESIS_FORCE_PURE_TRACER') == 'true'


class StateForActualGivenExecution(object):

    def __init__(self, test_runner, search_strategy, test, settings, random):
        self.test_runner = test_runner
        self.search_strategy = search_strategy
        self.settings = settings
        self.at_least_one_success = False
        self.last_exception = None
        self.repr_for_last_exception = None
        self.falsifying_examples = ()
        self.__was_flaky = False
        self.random = random
        self.__warned_deadline = False
        self.__existing_collector = None
        self.__test_runtime = None
        self.__in_final_replay = False

        if self.settings.deadline is None:
            self.test = test
        else:
            @proxies(test)
            def timed_test(*args, **kwargs):
                self.__test_runtime = None
                start = time.time()
                result = test(*args, **kwargs)
                runtime = (time.time() - start) * 1000
                self.__test_runtime = runtime
                if self.settings.deadline is not_set:
                    if (
                        not self.__warned_deadline and
                        runtime >= 200
                    ):
                        self.__warned_deadline = True
                        note_deprecation((
                            'Test took %.2fms to run. In future the default '
                            'deadline setting will be 200ms, which will '
                            'make this an error. You can set deadline to '
                            'an explicit value of e.g. %d to turn tests '
                            'slower than this into an error, or you can set '
                            'it to None to disable this check entirely.') % (
                                runtime, ceil(runtime / 100) * 100,
                        ))
                elif runtime >= self.current_deadline:
                    raise DeadlineExceeded(runtime, self.settings.deadline)
                return result
            self.test = timed_test

        self.coverage_data = CoverageData()
        self.files_to_propagate = set()

        if settings.use_coverage and not IN_COVERAGE_TESTS:  # pragma: no cover
            if Collector._collectors:
                self.hijack_collector(Collector._collectors[-1])

            self.collector = Collector(
                branch=True,
                timid=FORCE_PURE_TRACER,
                should_trace=self.should_trace,
                check_include=hypothesis_check_include,
                concurrency='thread',
                warn=escalate_warning,
            )
            self.collector.reset()

            # Hide the other collectors from this one so it doesn't attempt to
            # pause them (we're doing trace function management ourselves so
            # this will just cause problems).
            self.collector._collectors = []
        else:
            self.collector = None

    @property
    def current_deadline(self):
        base = self.settings.deadline
        if self.__in_final_replay:
            return base
        else:
            return base * 1.25

    def should_trace(self, original_filename, frame):  # pragma: no cover
        disp = FileDisposition()
        assert original_filename is not None
        disp.original_filename = original_filename
        disp.canonical_filename = encoded_filepath(
            canonical_filename(original_filename))
        disp.source_filename = disp.canonical_filename
        disp.reason = ''
        disp.file_tracer = None
        disp.has_dynamic_filename = False
        disp.trace = hypothesis_check_include(disp.canonical_filename)
        if not disp.trace:
            disp.reason = 'hypothesis internal reasons'
        elif self.__existing_collector is not None:
            check = self.__existing_collector.should_trace(
                original_filename, frame)
            if check.trace:
                self.files_to_propagate.add(check.canonical_filename)
        return disp

    def hijack_collector(self, collector):  # pragma: no cover
        self.__existing_collector = collector
        original_save_data = collector.save_data

        def save_data(covdata):
            original_save_data(covdata)
            if collector.branch:
                covdata.add_arcs({
                    filename: {
                        arc: None
                        for arc in self.coverage_data.arcs(filename)}
                    for filename in self.files_to_propagate
                })
            else:
                covdata.add_lines({
                    filename: {
                        line: None
                        for line in self.coverage_data.lines(filename)}
                    for filename in self.files_to_propagate
                })
            collector.save_data = original_save_data
        collector.save_data = save_data

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
            if self.collector is None:
                result = self.test_runner(data, reify_and_execute(
                    self.search_strategy, self.test,
                ))
            else:  # pragma: no cover
                # This should always be a no-op, but the coverage tracer has
                # a bad habit of resurrecting itself.
                original = sys.gettrace()
                sys.settrace(None)
                try:
                    self.collector.data = {}
                    result = self.test_runner(data, reify_and_execute(
                        self.search_strategy, self.test,
                        collector=self.collector
                    ))
                finally:
                    sys.settrace(original)
                    covdata = CoverageData()
                    self.collector.save_data(covdata)
                    self.coverage_data.update(covdata)
                    for filename in covdata.measured_files():
                        if is_hypothesis_file(filename):
                            continue
                        data.tags.update(
                            Arc(filename, source, target)
                            for source, target in covdata.arcs(filename)
                        )
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
        except Exception as e:
            escalate_hypothesis_internal_error()
            data.__expected_traceback = traceback.format_exc()
            data.__expected_exception = e
            verbose_report(data.__expected_traceback)

            error_class, _, tb = sys.exc_info()

            origin = traceback.extract_tb(tb)[-1]
            filename = origin[0]
            lineno = origin[1]
            data.mark_interesting((error_class, filename, lineno))

    def run(self):
        # Tell pytest to omit the body of this function from tracebacks
        __tracebackhide__ = True
        database_key = str_to_bytes(fully_qualified_name(self.test))
        self.start_time = time.time()
        global in_given
        runner = ConjectureRunner(
            self.evaluate_test_data,
            settings=self.settings, random=self.random,
            database_key=database_key,
        )

        if in_given or self.collector is None:
            runner.run()
        else:  # pragma: no cover
            in_given = True
            original_trace = sys.gettrace()
            try:
                sys.settrace(None)
                runner.run()
            finally:
                in_given = False
                sys.settrace(original_trace)
        note_engine_for_statistics(runner)
        run_time = time.time() - self.start_time
        timed_out = runner.exit_reason == ExitReason.timeout
        if runner.last_data is None:
            return
        if runner.interesting_examples:
            self.falsifying_examples = sorted(
                [d for d in runner.interesting_examples.values()],
                key=lambda d: sort_key(d.buffer), reverse=True
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

        if not self.falsifying_examples:
            return

        flaky = 0

        self.__in_final_replay = True

        for falsifying_example in self.falsifying_examples:
            self.__was_flaky = False
            raised_exception = False
            try:
                with self.settings:
                    self.test_runner(
                        ConjectureData.for_buffer(falsifying_example.buffer),
                        reify_and_execute(
                            self.search_strategy, self.test,
                            print_example=True, is_final=True
                        ))
            except (UnsatisfiedAssumption, StopTest):
                report(traceback.format_exc())
                self.__flaky(
                    'Unreliable assumption: An example which satisfied '
                    'assumptions on the first run now fails it.'
                )
            except:
                if len(self.falsifying_examples) <= 1:
                    raise
                raised_exception = True
                report(traceback.format_exc())

            if not raised_exception:
                if (
                    isinstance(
                        falsifying_example.__expected_exception,
                        DeadlineExceeded
                    ) and self.__test_runtime is not None
                ):
                    report((
                        'Unreliable test timings! On an initial run, this '
                        'test took %.2fms, which exceeded the deadline of '
                        '%.2fms, but on a subsequent run it took %.2f ms, '
                        'which did not. If you expect this sort of '
                        'variability in your test timings, consider turning '
                        'deadlines off for this test by setting deadline=None.'
                    ) % (
                        falsifying_example.__expected_exception.runtime,
                        self.settings.deadline, self.__test_runtime
                    ))
                else:
                    report(
                        'Failed to reproduce exception. Expected: \n' +
                        falsifying_example.__expected_traceback,
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
                        ConjectureData.for_buffer(falsifying_example.buffer),
                        reify_and_execute(
                            self.search_strategy,
                            test_is_flaky(
                                self.test, self.repr_for_last_exception),
                            print_example=True, is_final=True
                        ))
                except (UnsatisfiedAssumption, StopTest):
                    self.__flaky(filter_message)
                except Flaky as e:
                    if len(self.falsifying_examples) > 1:
                        self.__flaky(e.args[0])
                    else:
                        raise

            if self.__was_flaky:
                flaky += 1

        # If we only have one example then we should have raised an error or
        # flaky prior to this point.
        assert len(self.falsifying_examples) > 1

        if flaky > 0:
            raise Flaky((
                'Hypothesis found %d distinct failures, but %d of them '
                'exhibited some sort of flaky behaviour.') % (
                    len(self.falsifying_examples), flaky))
        else:
            raise MultipleFailures((
                'Hypothesis found %d distinct failures.') % (
                    len(self.falsifying_examples,)))

    def __flaky(self, message):
        if len(self.falsifying_examples) <= 1:
            raise Flaky(message)
        else:
            self.__was_flaky = True
            report('Flaky example! ' + message)


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

            try:
                perform_health_checks(
                    random, settings, test_runner, search_strategy)

                state = StateForActualGivenExecution(
                    test_runner, search_strategy, test, settings, random)
                state.run()
            except:
                generated_seed = \
                    wrapped_test._hypothesis_internal_use_generated_seed
                if generated_seed is not None:
                    if running_under_pytest:
                        report((
                            'You can add @seed(%(seed)d) to this test or run '
                            'pytest with --hypothesis-seed=%(seed)d to '
                            'reproduce this failure.') % {
                                'seed': generated_seed},)
                    else:
                        report((
                            'You can add @seed(%d) to this test to reproduce '
                            'this failure.') % (generated_seed,))
                raise

        for attrib in dir(test):
            if not (attrib.startswith('_') or hasattr(wrapped_test, attrib)):
                setattr(wrapped_test, attrib, getattr(test, attrib))
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
