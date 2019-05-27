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

"""This module provides the core primitives of Hypothesis, such as given."""


from __future__ import absolute_import, division, print_function

import ast
import base64
import contextlib
import datetime
import inspect
import os
import random as rnd_module
import traceback
import warnings
import zlib
from random import Random
from unittest import TestCase

import attr

import hypothesis.strategies as st
from hypothesis._settings import (
    HealthCheck,
    Phase,
    PrintSettings,
    Verbosity,
    local_settings,
    settings as Settings,
)
from hypothesis.control import BuildContext
from hypothesis.errors import (
    DeadlineExceeded,
    DidNotReproduce,
    FailedHealthCheck,
    Flaky,
    HypothesisDeprecationWarning,
    HypothesisWarning,
    InvalidArgument,
    MultipleFailures,
    NoSuchExample,
    Unsatisfiable,
    UnsatisfiedAssumption,
)
from hypothesis.executors import new_style_executor
from hypothesis.internal.compat import (
    PY2,
    bad_django_TestCase,
    benchmark_time,
    binary_type,
    get_type_hints,
    getfullargspec,
    hbytes,
    int_from_bytes,
    qualname,
)
from hypothesis.internal.conjecture.data import ConjectureData, StopTest
from hypothesis.internal.conjecture.engine import ConjectureRunner, ExitReason, sort_key
from hypothesis.internal.entropy import deterministic_PRNG
from hypothesis.internal.escalation import (
    escalate_hypothesis_internal_error,
    get_trimmed_traceback,
)
from hypothesis.internal.healthcheck import fail_health_check
from hypothesis.internal.reflection import (
    arg_string,
    convert_positional_arguments,
    define_function_signature,
    function_digest,
    get_pretty_function_description,
    impersonate,
    is_mock,
    nicerepr,
    proxies,
)
from hypothesis.reporting import current_verbosity, report, verbose_report
from hypothesis.searchstrategy.collections import TupleStrategy
from hypothesis.searchstrategy.strategies import SearchStrategy
from hypothesis.statistics import note_engine_for_statistics
from hypothesis.utils.conventions import infer
from hypothesis.version import __version__

if False:
    from typing import Any, Dict, Callable, Hashable, Optional, Union, TypeVar  # noqa
    from hypothesis.utils.conventions import InferType  # noqa

    TestFunc = TypeVar("TestFunc", bound=Callable)


running_under_pytest = False
global_force_seed = None


def new_random():
    return rnd_module.Random(rnd_module.getrandbits(128))


@attr.s()
class Example(object):
    args = attr.ib()
    kwargs = attr.ib()


def example(*args, **kwargs):
    # type: (*Any, **Any) -> Callable[[TestFunc], TestFunc]
    """A decorator which ensures a specific example is always tested."""
    if args and kwargs:
        raise InvalidArgument(
            "Cannot mix positional and keyword arguments for examples"
        )
    if not (args or kwargs):
        raise InvalidArgument("An example must provide at least one argument")

    def accept(test):
        if not hasattr(test, "hypothesis_explicit_examples"):
            test.hypothesis_explicit_examples = []
        test.hypothesis_explicit_examples.append(Example(tuple(args), kwargs))
        return test

    return accept


def seed(seed):
    # type: (Hashable) -> Callable[[TestFunc], TestFunc]
    """seed: Start the test execution from a specific seed.

    May be any hashable object. No exact meaning for seed is provided
    other than that for a fixed seed value Hypothesis will try the same
    actions (insofar as it can given external sources of non-
    determinism. e.g. timing and hash randomization).

    Overrides the derandomize setting, which is designed to enable
    deterministic builds rather than reproducing observed failures.

    """

    def accept(test):
        test._hypothesis_internal_use_seed = seed
        current_settings = getattr(test, "_hypothesis_internal_use_settings", None)
        test._hypothesis_internal_use_settings = Settings(
            current_settings, database=None
        )
        return test

    return accept


def reproduce_failure(version, blob):
    """Run the example that corresponds to this data blob in order to reproduce
    a failure.

    A test with this decorator *always* runs only one example and always fails.
    If the provided example does not cause a failure, or is in some way invalid
    for this test, then this will fail with a DidNotReproduce error.

    This decorator is not intended to be a permanent addition to your test
    suite. It's simply some code you can add to ease reproduction of a problem
    in the event that you don't have access to the test database. Because of
    this, *no* compatibility guarantees are made between different versions of
    Hypothesis - its API may change arbitrarily from version to version.
    """

    def accept(test):
        test._hypothesis_internal_use_reproduce_failure = (version, blob)
        return test

    return accept


def encode_failure(buffer):
    # This needs to be a real bytes() instance, so we use binary_type()
    # instead of hbytes() here.
    buffer = binary_type(buffer)
    compressed = zlib.compress(buffer)
    if len(compressed) < len(buffer):
        buffer = b"\1" + compressed
    else:
        buffer = b"\0" + buffer
    return base64.b64encode(buffer)


def decode_failure(blob):
    try:
        buffer = base64.b64decode(blob)
    except Exception:
        raise InvalidArgument("Invalid base64 encoded string: %r" % (blob,))
    prefix = buffer[:1]
    if prefix == b"\0":
        return buffer[1:]
    elif prefix == b"\1":
        try:
            return zlib.decompress(buffer[1:])
        except zlib.error:
            raise InvalidArgument("Invalid zlib compression for blob %r" % (blob,))
    else:
        raise InvalidArgument(
            "Could not decode blob %r: Invalid start byte %r" % (blob, prefix)
        )


class WithRunner(SearchStrategy):
    def __init__(self, base, runner):
        assert runner is not None
        self.base = base
        self.runner = runner

    def do_draw(self, data):
        data.hypothesis_runner = self.runner
        return self.base.do_draw(data)


def is_invalid_test(name, original_argspec, generator_arguments, generator_kwargs):
    def invalid(message):
        def wrapped_test(*arguments, **kwargs):
            raise InvalidArgument(message)

        wrapped_test.is_hypothesis_test = True
        return wrapped_test

    if not (generator_arguments or generator_kwargs):
        return invalid("given must be called with at least one argument")

    if generator_arguments and any(
        [original_argspec.varargs, original_argspec.varkw, original_argspec.kwonlyargs]
    ):
        return invalid(
            "positional arguments to @given are not supported with varargs, "
            "varkeywords, or keyword-only arguments"
        )

    if len(generator_arguments) > len(original_argspec.args):
        args = tuple(generator_arguments)
        return invalid(
            "Too many positional arguments for %s() were passed to @given "
            "- expected at most %d arguments, but got %d %r"
            % (name, len(original_argspec.args), len(args), args)
        )

    if infer in generator_arguments:
        return invalid(
            "infer was passed as a positional argument to @given, "
            "but may only be passed as a keyword argument"
        )

    if generator_arguments and generator_kwargs:
        return invalid("cannot mix positional and keyword arguments to @given")
    extra_kwargs = [
        k
        for k in generator_kwargs
        if k not in original_argspec.args + original_argspec.kwonlyargs
    ]
    if extra_kwargs and not original_argspec.varkw:
        arg = extra_kwargs[0]
        return invalid(
            "%s() got an unexpected keyword argument %r, from `%s=%r` in @given"
            % (name, arg, arg, generator_kwargs[arg])
        )
    for a in original_argspec.args:
        if isinstance(a, list):  # pragma: no cover
            return invalid(
                "Cannot decorate function %s() because it has destructuring arguments"
                % (name,)
            )
    if original_argspec.defaults or original_argspec.kwonlydefaults:
        return invalid("Cannot apply @given to a function with defaults.")
    missing = [
        repr(kw) for kw in original_argspec.kwonlyargs if kw not in generator_kwargs
    ]
    if missing:
        raise InvalidArgument(
            "Missing required kwarg{}: {}".format(
                "s" if len(missing) > 1 else "", ", ".join(missing)
            )
        )


def execute_explicit_examples(
    test_runner, test, wrapped_test, settings, arguments, kwargs
):
    original_argspec = getfullargspec(test)

    for example in reversed(getattr(wrapped_test, "hypothesis_explicit_examples", ())):
        example_kwargs = dict(original_argspec.kwonlydefaults or {})
        if example.args:
            if len(example.args) > len(original_argspec.args):
                raise InvalidArgument(
                    "example has too many arguments for test. "
                    "Expected at most %d but got %d"
                    % (len(original_argspec.args), len(example.args))
                )
            example_kwargs.update(
                dict(zip(original_argspec.args[-len(example.args) :], example.args))
            )
        else:
            example_kwargs.update(example.kwargs)
        if Phase.explicit not in settings.phases:
            continue
        example_kwargs.update(kwargs)
        # Note: Test may mutate arguments and we can't rerun explicit
        # examples, so we have to calculate the failure message at this
        # point rather than than later.
        example_string = "%s(%s)" % (
            test.__name__,
            arg_string(test, arguments, example_kwargs),
        )
        with local_settings(settings):
            try:
                with BuildContext(None) as b:
                    verbose_report("Trying example: " + example_string)
                    test_runner(None, lambda data: test(*arguments, **example_kwargs))
            except BaseException:
                report("Falsifying example: " + example_string)
                for n in b.notes:
                    report(n)
                raise


def get_random_for_wrapped_test(test, wrapped_test):
    settings = wrapped_test._hypothesis_internal_use_settings
    wrapped_test._hypothesis_internal_use_generated_seed = None

    if wrapped_test._hypothesis_internal_use_seed is not None:
        return Random(wrapped_test._hypothesis_internal_use_seed)
    elif settings.derandomize:
        return Random(int_from_bytes(function_digest(test)))
    elif global_force_seed is not None:
        return Random(global_force_seed)
    else:
        seed = rnd_module.getrandbits(128)
        wrapped_test._hypothesis_internal_use_generated_seed = seed
        return Random(seed)


def process_arguments_to_given(
    wrapped_test,
    arguments,
    kwargs,
    generator_arguments,
    generator_kwargs,
    argspec,
    test,
    settings,
):
    selfy = None
    arguments, kwargs = convert_positional_arguments(wrapped_test, arguments, kwargs)

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

    # We use TupleStrategy over tuples() here to avoid polluting
    # st.STRATEGY_CACHE with references (see #493), and because this is
    # trivial anyway if the fixed_dictionaries strategy is cacheable.
    search_strategy = TupleStrategy(
        (
            st.just(arguments),
            st.fixed_dictionaries(generator_kwargs).map(
                lambda args: dict(args, **kwargs)
            ),
        )
    )

    if selfy is not None:
        search_strategy = WithRunner(search_strategy, selfy)

    search_strategy.validate()

    return arguments, kwargs, test_runner, search_strategy


def run_once(fn):
    """Wraps a no-args function so that its outcome is cached.
    We use this for calculating various lists of exceptions
    the first time we use them."""
    result = [None]

    def run():
        if result[0] is None:
            result[0] = fn()
            assert result[0] is not None
        return result[0]

    run.__name__ = fn.__name__
    return run


@run_once
def skip_exceptions_to_reraise():
    """Return a tuple of exceptions meaning 'skip this test', to re-raise.

    This is intended to cover most common test runners; if you would
    like another to be added please open an issue or pull request.
    """
    import unittest

    # This is a set because nose may simply re-export unittest.SkipTest
    exceptions = {unittest.SkipTest}

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


@run_once
def failure_exceptions_to_catch():
    """Return a tuple of exceptions meaning 'this test has failed', to catch.

    This is intended to cover most common test runners; if you would
    like another to be added please open an issue or pull request.
    """
    exceptions = [Exception]
    try:  # pragma: no cover
        from _pytest.outcomes import Failed

        exceptions.append(Failed)
    except ImportError:
        pass
    return tuple(exceptions)


def new_given_argspec(original_argspec, generator_kwargs):
    """Make an updated argspec for the wrapped test."""
    new_args = [a for a in original_argspec.args if a not in generator_kwargs]
    new_kwonlyargs = [
        a for a in original_argspec.kwonlyargs if a not in generator_kwargs
    ]
    annots = {
        k: v
        for k, v in original_argspec.annotations.items()
        if k in new_args + new_kwonlyargs
    }
    annots["return"] = None
    return original_argspec._replace(
        args=new_args, kwonlyargs=new_kwonlyargs, annotations=annots
    )


ROOT = os.path.dirname(__file__)

STDLIB = os.path.dirname(os.__file__)


class StateForActualGivenExecution(object):
    def __init__(self, test_runner, search_strategy, test, settings, random, had_seed):
        self.test_runner = test_runner
        self.search_strategy = search_strategy
        self.settings = settings
        self.last_exception = None
        self.falsifying_examples = ()
        self.__was_flaky = False
        self.random = random
        self.__warned_deadline = False
        self.__test_runtime = None
        self.__had_seed = had_seed

        self.test = test

        self.files_to_propagate = set()
        self.failed_normally = False

        self.used_examples_from_database = False

    def execute(
        self,
        data,
        print_example=False,
        is_final=False,
        expected_failure=None,
        collect=False,
    ):
        text_repr = [None]
        if self.settings.deadline is None:
            test = self.test
        else:

            @proxies(self.test)
            def test(*args, **kwargs):
                self.__test_runtime = None
                initial_draws = len(data.draw_times)
                start = benchmark_time()
                result = self.test(*args, **kwargs)
                finish = benchmark_time()
                internal_draw_time = sum(data.draw_times[initial_draws:])
                runtime = datetime.timedelta(
                    seconds=finish - start - internal_draw_time
                )
                self.__test_runtime = runtime
                current_deadline = self.settings.deadline
                if not is_final:
                    current_deadline = (current_deadline // 4) * 5
                if runtime >= current_deadline:
                    raise DeadlineExceeded(runtime, self.settings.deadline)
                return result

        def run(data):
            if not hasattr(data, "can_reproduce_example_from_repr"):
                data.can_reproduce_example_from_repr = True
            with local_settings(self.settings):
                with deterministic_PRNG():
                    with BuildContext(data, is_final=is_final):
                        args, kwargs = data.draw(self.search_strategy)
                        if expected_failure is not None:
                            text_repr[0] = arg_string(test, args, kwargs)

                        if print_example:
                            example = "%s(%s)" % (
                                test.__name__,
                                arg_string(test, args, kwargs),
                            )
                            try:
                                ast.parse(example)
                            except SyntaxError:
                                data.can_reproduce_example_from_repr = False
                            report("Falsifying example: %s" % (example,))
                        elif current_verbosity() >= Verbosity.verbose:
                            report(
                                lambda: "Trying example: %s(%s)"
                                % (test.__name__, arg_string(test, args, kwargs))
                            )
                        return test(*args, **kwargs)

        result = self.test_runner(data, run)
        if expected_failure is not None:
            exception, traceback = expected_failure
            if (
                isinstance(exception, DeadlineExceeded)
                and self.__test_runtime is not None
            ):
                report(
                    (
                        "Unreliable test timings! On an initial run, this "
                        "test took %.2fms, which exceeded the deadline of "
                        "%.2fms, but on a subsequent run it took %.2f ms, "
                        "which did not. If you expect this sort of "
                        "variability in your test timings, consider turning "
                        "deadlines off for this test by setting deadline=None."
                    )
                    % (
                        exception.runtime.total_seconds() * 1000,
                        self.settings.deadline.total_seconds() * 1000,
                        self.__test_runtime.total_seconds() * 1000,
                    )
                )
            else:
                report("Failed to reproduce exception. Expected: \n" + traceback)
            self.__flaky(
                (
                    "Hypothesis %s(%s) produces unreliable results: Falsified"
                    " on the first call but did not on a subsequent one"
                )
                % (test.__name__, text_repr[0])
            )
        return result

    def evaluate_test_data(self, data):
        try:
            result = self.execute(data)
            if result is not None:
                fail_health_check(
                    self.settings,
                    (
                        "Tests run under @given should return None, but "
                        "%s returned %r instead."
                    )
                    % (self.test.__name__, result),
                    HealthCheck.return_value,
                )
        except UnsatisfiedAssumption:
            data.mark_invalid()
        except (
            HypothesisDeprecationWarning,
            FailedHealthCheck,
            StopTest,
        ) + skip_exceptions_to_reraise():
            raise
        except failure_exceptions_to_catch() as e:
            escalate_hypothesis_internal_error()
            if data.frozen:
                # This can happen if an error occurred in a finally
                # block somewhere, suppressing our original StopTest.
                # We raise a new one here to resume normal operation.
                raise StopTest(data.testcounter)
            else:
                tb = get_trimmed_traceback()
                info = data.extra_information
                info.__expected_traceback = "".join(
                    traceback.format_exception(type(e), e, tb)
                )
                info.__expected_exception = e
                verbose_report(info.__expected_traceback)

                origin = traceback.extract_tb(tb)[-1]
                filename = origin[0]
                lineno = origin[1]
                data.mark_interesting((type(e), filename, lineno))

    def run(self):
        # Tell pytest to omit the body of this function from tracebacks
        __tracebackhide__ = True
        if global_force_seed is None:
            database_key = function_digest(self.test)
        else:
            database_key = None
        runner = ConjectureRunner(
            self.evaluate_test_data,
            settings=self.settings,
            random=self.random,
            database_key=database_key,
        )
        try:
            runner.run()
        finally:
            self.used_examples_from_database = runner.used_examples_from_database
        note_engine_for_statistics(runner)

        self.used_examples_from_database = runner.used_examples_from_database

        if runner.call_count == 0:
            return
        if runner.interesting_examples:
            self.falsifying_examples = sorted(
                [d for d in runner.interesting_examples.values()],
                key=lambda d: sort_key(d.buffer),
                reverse=True,
            )
        else:
            if runner.valid_examples == 0:
                raise Unsatisfiable(
                    "Unable to satisfy assumptions of hypothesis %s."
                    % (get_pretty_function_description(self.test),)
                )

        if not self.falsifying_examples:
            return
        elif not self.settings.report_multiple_bugs:
            del self.falsifying_examples[:-1]

        self.failed_normally = True

        flaky = 0

        for falsifying_example in self.falsifying_examples:
            info = falsifying_example.extra_information

            ran_example = ConjectureData.for_buffer(falsifying_example.buffer)
            self.__was_flaky = False
            assert info.__expected_exception is not None
            try:
                self.execute(
                    ran_example,
                    print_example=True,
                    is_final=True,
                    expected_failure=(
                        info.__expected_exception,
                        info.__expected_traceback,
                    ),
                )
            except (UnsatisfiedAssumption, StopTest):
                report(traceback.format_exc())
                self.__flaky(
                    "Unreliable assumption: An example which satisfied "
                    "assumptions on the first run now fails it."
                )
            except BaseException as e:
                if len(self.falsifying_examples) <= 1:
                    raise
                tb = get_trimmed_traceback()
                report("".join(traceback.format_exception(type(e), e, tb)))
            finally:  # pragma: no cover
                # This section is in fact entirely covered by the tests in
                # test_reproduce_failure, but it seems to trigger a lovely set
                # of coverage bugs: The branches show up as uncovered (despite
                # definitely being covered - you can add an assert False else
                # branch to verify this and see it fail - and additionally the
                # second branch still complains about lack of coverage even if
                # you add a pragma: no cover to it!
                # See https://bitbucket.org/ned/coveragepy/issues/623/
                if self.settings.print_blob is not PrintSettings.NEVER:
                    failure_blob = encode_failure(falsifying_example.buffer)
                    # Have to use the example we actually ran, not the original
                    # falsifying example! Otherwise we won't catch problems
                    # where the repr of the generated example doesn't parse.
                    can_use_repr = ran_example.can_reproduce_example_from_repr
                    if self.settings.print_blob is PrintSettings.ALWAYS or (
                        self.settings.print_blob is PrintSettings.INFER
                        and self.settings.verbosity >= Verbosity.normal
                        and not can_use_repr
                        and len(failure_blob) < 200
                    ):
                        report(
                            (
                                "\nYou can reproduce this example by temporarily "
                                "adding @reproduce_failure(%r, %r) as a decorator "
                                "on your test case"
                            )
                            % (__version__, failure_blob)
                        )
            if self.__was_flaky:
                flaky += 1

        # If we only have one example then we should have raised an error or
        # flaky prior to this point.
        assert len(self.falsifying_examples) > 1

        if flaky > 0:
            raise Flaky(
                (
                    "Hypothesis found %d distinct failures, but %d of them "
                    "exhibited some sort of flaky behaviour."
                )
                % (len(self.falsifying_examples), flaky)
            )
        else:
            raise MultipleFailures(
                ("Hypothesis found %d distinct failures.")
                % (len(self.falsifying_examples))
            )

    def __flaky(self, message):
        if len(self.falsifying_examples) <= 1:
            raise Flaky(message)
        else:
            self.__was_flaky = True
            report("Flaky example! " + message)


@contextlib.contextmanager
def fake_subTest(self, msg=None, **__):
    """Monkeypatch for `unittest.TestCase.subTest` during `@given`.

    If we don't patch this out, each failing example is reported as a
    seperate failing test by the unittest test runner, which is
    obviously incorrect. We therefore replace it for the duration with
    this version.
    """
    warnings.warn(
        "subTest per-example reporting interacts badly with Hypothesis "
        "trying hundreds of examples, so we disable it for the duration of "
        "any test that uses `@given`.",
        HypothesisWarning,
        stacklevel=2,
    )
    yield


@attr.s()
class HypothesisHandle(object):
    """This object is provided as the .hypothesis attribute on @given tests.

    Downstream users can reassign its attributes to insert custom logic into
    the execution of each case, for example by converting an async into a
    sync function.

    This must be an attribute of an attribute, because reassignment of a
    first-level attribute would not be visible to Hypothesis if the function
    had been decorated before the assignment.

    See https://github.com/HypothesisWorks/hypothesis/issues/1257 for more
    information.
    """

    inner_test = attr.ib()


def given(
    *given_arguments,  # type: Union[SearchStrategy, InferType]
    **given_kwargs  # type: Union[SearchStrategy, InferType]
):
    # type: (...) -> Callable[[Callable[..., None]], Callable[..., None]]
    """A decorator for turning a test function that accepts arguments into a
    randomized test.

    This is the main entry point to Hypothesis.
    """

    def run_test_with_generator(test):
        if hasattr(test, "_hypothesis_internal_test_function_without_warning"):
            # Pull out the original test function to avoid the warning we
            # stuck in about using @settings without @given.
            test = test._hypothesis_internal_test_function_without_warning
        if inspect.isclass(test):
            # Provide a meaningful error to users, instead of exceptions from
            # internals that assume we're dealing with a function.
            raise InvalidArgument("@given cannot be applied to a class.")
        generator_arguments = tuple(given_arguments)
        generator_kwargs = dict(given_kwargs)

        original_argspec = getfullargspec(test)

        check_invalid = is_invalid_test(
            test.__name__, original_argspec, generator_arguments, generator_kwargs
        )

        if check_invalid is not None:
            return check_invalid

        for name, strategy in zip(
            reversed(original_argspec.args), reversed(generator_arguments)
        ):
            generator_kwargs[name] = strategy

        argspec = new_given_argspec(original_argspec, generator_kwargs)

        @impersonate(test)
        @define_function_signature(test.__name__, test.__doc__, argspec)
        def wrapped_test(*arguments, **kwargs):
            # Tell pytest to omit the body of this function from tracebacks
            __tracebackhide__ = True

            test = wrapped_test.hypothesis.inner_test

            if getattr(test, "is_hypothesis_test", False):
                raise InvalidArgument(
                    (
                        "You have applied @given to the test %s more than once, which "
                        "wraps the test several times and is extremely slow. A "
                        "similar effect can be gained by combining the arguments "
                        "of the two calls to given. For example, instead of "
                        "@given(booleans()) @given(integers()), you could write "
                        "@given(booleans(), integers())"
                    )
                    % (test.__name__,)
                )

            settings = wrapped_test._hypothesis_internal_use_settings

            random = get_random_for_wrapped_test(test, wrapped_test)

            if infer in generator_kwargs.values():
                hints = get_type_hints(test)
            for name in [
                name for name, value in generator_kwargs.items() if value is infer
            ]:
                if name not in hints:
                    raise InvalidArgument(
                        "passed %s=infer for %s, but %s has no type annotation"
                        % (name, test.__name__, name)
                    )
                generator_kwargs[name] = st.from_type(hints[name])

            processed_args = process_arguments_to_given(
                wrapped_test,
                arguments,
                kwargs,
                generator_arguments,
                generator_kwargs,
                argspec,
                test,
                settings,
            )
            arguments, kwargs, test_runner, search_strategy = processed_args

            runner = getattr(search_strategy, "runner", None)
            if isinstance(runner, TestCase) and test.__name__ in dir(TestCase):
                msg = (
                    "You have applied @given to the method %s, which is "
                    "used by the unittest runner but is not itself a test."
                    "  This is not useful in any way." % test.__name__
                )
                fail_health_check(settings, msg, HealthCheck.not_a_test_method)
            if bad_django_TestCase(runner):  # pragma: no cover
                # Covered by the Django tests, but not the pytest coverage task
                raise InvalidArgument(
                    "You have applied @given to a method on %s, but this "
                    "class does not inherit from the supported versions in "
                    "`hypothesis.extra.django`.  Use the Hypothesis variants "
                    "to ensure that each example is run in a separate "
                    "database transaction." % qualname(type(runner))
                )

            state = StateForActualGivenExecution(
                test_runner,
                search_strategy,
                test,
                settings,
                random,
                had_seed=wrapped_test._hypothesis_internal_use_seed,
            )

            reproduce_failure = wrapped_test._hypothesis_internal_use_reproduce_failure

            if reproduce_failure is not None:
                expected_version, failure = reproduce_failure
                if expected_version != __version__:
                    raise InvalidArgument(
                        (
                            "Attempting to reproduce a failure from a different "
                            "version of Hypothesis. This failure is from %s, but "
                            "you are currently running %r. Please change your "
                            "Hypothesis version to a matching one."
                        )
                        % (expected_version, __version__)
                    )
                try:
                    state.execute(
                        ConjectureData.for_buffer(decode_failure(failure)),
                        print_example=True,
                        is_final=True,
                    )
                    raise DidNotReproduce(
                        "Expected the test to raise an error, but it "
                        "completed successfully."
                    )
                except StopTest:
                    raise DidNotReproduce(
                        "The shape of the test data has changed in some way "
                        "from where this blob was defined. Are you sure "
                        "you're running the same test?"
                    )
                except UnsatisfiedAssumption:
                    raise DidNotReproduce(
                        "The test data failed to satisfy an assumption in the "
                        "test. Have you added it since this blob was "
                        "generated?"
                    )

            execute_explicit_examples(
                test_runner, test, wrapped_test, settings, arguments, kwargs
            )

            if settings.max_examples <= 0:
                return

            if not (
                Phase.reuse in settings.phases or Phase.generate in settings.phases
            ):
                return

            try:
                if isinstance(runner, TestCase) and hasattr(runner, "subTest"):
                    subTest = runner.subTest
                    try:
                        setattr(runner, "subTest", fake_subTest)
                        state.run()
                    finally:
                        setattr(runner, "subTest", subTest)
                else:
                    state.run()
            except BaseException as e:
                generated_seed = wrapped_test._hypothesis_internal_use_generated_seed
                with local_settings(settings):
                    if not (state.failed_normally or generated_seed is None):
                        if running_under_pytest:
                            report(
                                "You can add @seed(%(seed)d) to this test or "
                                "run pytest with --hypothesis-seed=%(seed)d "
                                "to reproduce this failure." % {"seed": generated_seed}
                            )
                        else:
                            report(
                                "You can add @seed(%d) to this test to "
                                "reproduce this failure." % (generated_seed,)
                            )
                    # The dance here is to avoid showing users long tracebacks
                    # full of Hypothesis internals they don't care about.
                    # We have to do this inline, to avoid adding another
                    # internal stack frame just when we've removed the rest.
                    if PY2:
                        # Python 2 doesn't have Exception.with_traceback(...);
                        # instead it has a three-argument form of the `raise`
                        # statement.  Unfortunately this is a SyntaxError on
                        # Python 3, and before Python 2.7.9 it was *also* a
                        # SyntaxError to use it in a nested function so we
                        # can't `exec` or `eval` our way out (BPO-21591).
                        # So unless we break some versions of Python 2, none
                        # of them get traceback elision.
                        raise
                    # On Python 3, we swap out the real traceback for our
                    # trimmed version.  Using a variable ensures that the line
                    # which will actually appear in trackbacks is as clear as
                    # possible - "raise the_error_hypothesis_found".
                    the_error_hypothesis_found = e.with_traceback(
                        get_trimmed_traceback()
                    )
                    raise the_error_hypothesis_found

        for attrib in dir(test):
            if not (attrib.startswith("_") or hasattr(wrapped_test, attrib)):
                setattr(wrapped_test, attrib, getattr(test, attrib))
        wrapped_test.is_hypothesis_test = True
        if hasattr(test, "_hypothesis_internal_settings_applied"):
            # Used to check if @settings is applied twice.
            wrapped_test._hypothesis_internal_settings_applied = True
        wrapped_test._hypothesis_internal_use_seed = getattr(
            test, "_hypothesis_internal_use_seed", None
        )
        wrapped_test._hypothesis_internal_use_settings = (
            getattr(test, "_hypothesis_internal_use_settings", None) or Settings.default
        )
        wrapped_test._hypothesis_internal_use_reproduce_failure = getattr(
            test, "_hypothesis_internal_use_reproduce_failure", None
        )
        wrapped_test.hypothesis = HypothesisHandle(test)
        return wrapped_test

    return run_test_with_generator


def find(
    specifier,  # type: SearchStrategy
    condition,  # type: Callable[[Any], bool]
    settings=None,  # type: Settings
    random=None,  # type: Any
    database_key=None,  # type: bytes
):
    # type: (...) -> Any
    """Returns the minimal example from the given strategy ``specifier`` that
    matches the predicate function ``condition``."""
    if settings is None:
        settings = Settings(max_examples=2000)
    settings = Settings(settings, suppress_health_check=HealthCheck.all())

    if database_key is None and settings.database is not None:
        database_key = function_digest(condition)

    if not isinstance(specifier, SearchStrategy):
        raise InvalidArgument(
            "Expected SearchStrategy but got %r of type %s"
            % (specifier, type(specifier).__name__)
        )
    specifier.validate()

    search = specifier

    random = random or new_random()
    successful_examples = [0]
    last_data = [None]
    last_repr = [None]

    def template_condition(data):
        with deterministic_PRNG():
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

        if settings.verbosity >= Verbosity.verbose:
            if not successful_examples[0]:
                report(u"Tried non-satisfying example %s" % (nicerepr(result),))
            elif success:
                if successful_examples[0] == 1:
                    last_repr[0] = nicerepr(result)
                    report(u"Found satisfying example %s" % (last_repr[0],))
                    last_data[0] = data
                elif (
                    sort_key(hbytes(data.buffer)) < sort_key(last_data[0].buffer)
                ) and nicerepr(result) != last_repr[0]:
                    last_repr[0] = nicerepr(result)
                    report(u"Shrunk example to %s" % (last_repr[0],))
                    last_data[0] = data
        if success and not data.frozen:
            data.mark_interesting()

    runner = ConjectureRunner(
        template_condition, settings=settings, random=random, database_key=database_key
    )
    runner.run()
    note_engine_for_statistics(runner)
    if runner.interesting_examples:
        data = ConjectureData.for_buffer(
            list(runner.interesting_examples.values())[0].buffer
        )
        with deterministic_PRNG():
            with BuildContext(data):
                return data.draw(search)
    if runner.valid_examples == 0 and (runner.exit_reason != ExitReason.finished):
        raise Unsatisfiable(
            "Unable to satisfy assumptions of %s."
            % (get_pretty_function_description(condition),)
        )

    raise NoSuchExample(get_pretty_function_description(condition))
