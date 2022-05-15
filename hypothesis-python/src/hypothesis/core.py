# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""This module provides the core primitives of Hypothesis, such as given."""

import base64
import contextlib
import datetime
import inspect
import io
import sys
import time
import types
import warnings
import zlib
from collections import defaultdict
from io import StringIO
from itertools import chain
from random import Random
from typing import (
    Any,
    BinaryIO,
    Callable,
    Coroutine,
    Hashable,
    List,
    Optional,
    TypeVar,
    Union,
    overload,
)
from unittest import TestCase

import attr

from hypothesis import strategies as st
from hypothesis._settings import (
    HealthCheck,
    Phase,
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
    Found,
    HypothesisDeprecationWarning,
    HypothesisWarning,
    InvalidArgument,
    MultipleFailures,
    NoSuchExample,
    StopTest,
    Unsatisfiable,
    UnsatisfiedAssumption,
)
from hypothesis.executors import default_new_style_executor, new_style_executor
from hypothesis.internal.compat import (
    PYPY,
    bad_django_TestCase,
    get_type_hints,
    int_from_bytes,
)
from hypothesis.internal.conjecture.data import ConjectureData, Status
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.internal.conjecture.shrinker import sort_key
from hypothesis.internal.entropy import deterministic_PRNG
from hypothesis.internal.escalation import (
    escalate_hypothesis_internal_error,
    format_exception,
    get_interesting_origin,
    get_trimmed_traceback,
)
from hypothesis.internal.healthcheck import fail_health_check
from hypothesis.internal.reflection import (
    convert_positional_arguments,
    define_function_signature,
    function_digest,
    get_pretty_function_description,
    getfullargspec_except_self as getfullargspec,
    impersonate,
    is_mock,
    proxies,
    repr_call,
)
from hypothesis.internal.scrutineer import Tracer, explanatory_lines
from hypothesis.reporting import (
    current_verbosity,
    report,
    verbose_report,
    with_reporter,
)
from hypothesis.statistics import describe_targets, note_statistics
from hypothesis.strategies._internal.collections import TupleStrategy
from hypothesis.strategies._internal.misc import NOTHING
from hypothesis.strategies._internal.strategies import (
    Ex,
    MappedSearchStrategy,
    SearchStrategy,
)
from hypothesis.utils.conventions import infer
from hypothesis.vendor.pretty import RepresentationPrinter
from hypothesis.version import __version__

if sys.version_info >= (3, 10):  # pragma: no cover
    from types import EllipsisType as InferType

else:
    InferType = type(Ellipsis)


TestFunc = TypeVar("TestFunc", bound=Callable)


running_under_pytest = False
global_force_seed = None
_hypothesis_global_random = None


@attr.s()
class Example:
    args = attr.ib()
    kwargs = attr.ib()


def example(*args: Any, **kwargs: Any) -> Callable[[TestFunc], TestFunc]:
    """A decorator which ensures a specific example is always tested."""
    if args and kwargs:
        raise InvalidArgument(
            "Cannot mix positional and keyword arguments for examples"
        )
    if not (args or kwargs):
        raise InvalidArgument("An example must provide at least one argument")

    hypothesis_explicit_examples: List[Example] = []

    def accept(test):
        if not hasattr(test, "hypothesis_explicit_examples"):
            test.hypothesis_explicit_examples = hypothesis_explicit_examples
        test.hypothesis_explicit_examples.append(Example(tuple(args), kwargs))
        return test

    accept.hypothesis_explicit_examples = hypothesis_explicit_examples  # type: ignore
    return accept


def seed(seed: Hashable) -> Callable[[TestFunc], TestFunc]:
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


def reproduce_failure(version: str, blob: bytes) -> Callable[[TestFunc], TestFunc]:
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
    buffer = bytes(buffer)
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
        raise InvalidArgument(f"Invalid base64 encoded string: {blob!r}") from None
    prefix = buffer[:1]
    if prefix == b"\0":
        return buffer[1:]
    elif prefix == b"\1":
        try:
            return zlib.decompress(buffer[1:])
        except zlib.error as err:
            raise InvalidArgument(
                f"Invalid zlib compression for blob {blob!r}"
            ) from err
    else:
        raise InvalidArgument(
            f"Could not decode blob {blob!r}: Invalid start byte {prefix!r}"
        )


class WithRunner(MappedSearchStrategy):
    def __init__(self, base, runner):
        assert runner is not None
        super().__init__(base)
        self.runner = runner

    def do_draw(self, data):
        data.hypothesis_runner = self.runner
        return self.mapped_strategy.do_draw(data)

    def __repr__(self):
        return f"WithRunner({self.mapped_strategy!r}, runner={self.runner!r})"


def is_invalid_test(test, original_argspec, given_arguments, given_kwargs):
    """Check the arguments to ``@given`` for basic usage constraints.

    Most errors are not raised immediately; instead we return a dummy test
    function that will raise the appropriate error if it is actually called.
    When the user runs a subset of tests (e.g via ``pytest -k``), errors will
    only be reported for tests that actually ran.
    """

    def invalid(message, *, exc=InvalidArgument):
        def wrapped_test(*arguments, **kwargs):
            raise exc(message)

        wrapped_test.is_hypothesis_test = True
        wrapped_test.hypothesis = HypothesisHandle(
            inner_test=test,
            get_fuzz_target=wrapped_test,
            given_kwargs=given_kwargs,
        )
        return wrapped_test

    if not (given_arguments or given_kwargs):
        return invalid("given must be called with at least one argument")

    if given_arguments and any(
        [original_argspec.varargs, original_argspec.varkw, original_argspec.kwonlyargs]
    ):
        return invalid(
            "positional arguments to @given are not supported with varargs, "
            "varkeywords, or keyword-only arguments"
        )

    if len(given_arguments) > len(original_argspec.args):
        args = tuple(given_arguments)
        return invalid(
            f"Too many positional arguments for {test.__name__}() were passed to "
            f"@given - expected at most {int(len(original_argspec.args))} "
            f"arguments, but got {int(len(args))} {args!r}"
        )

    if infer in given_arguments:
        return invalid(
            "... was passed as a positional argument to @given, "
            "but may only be passed as a keyword argument or as "
            "the sole argument of @given"
        )

    if given_arguments and given_kwargs:
        return invalid("cannot mix positional and keyword arguments to @given")
    extra_kwargs = [
        k
        for k in given_kwargs
        if k not in original_argspec.args + original_argspec.kwonlyargs
    ]
    if extra_kwargs and not original_argspec.varkw:
        arg = extra_kwargs[0]
        return invalid(
            f"{test.__name__}() got an unexpected keyword argument {arg!r}, "
            f"from `{arg}={given_kwargs[arg]!r}` in @given"
        )
    if original_argspec.defaults or original_argspec.kwonlydefaults:
        return invalid("Cannot apply @given to a function with defaults.")
    missing = [repr(kw) for kw in original_argspec.kwonlyargs if kw not in given_kwargs]
    if missing:
        return invalid(
            "Missing required kwarg{}: {}".format(
                "s" if len(missing) > 1 else "", ", ".join(missing)
            )
        )

    # This case would raise Unsatisfiable *anyway*, but by detecting it here we can
    # provide a much more helpful error message for people e.g. using the Ghostwriter.
    empty = [
        f"{s!r} (arg {idx})" for idx, s in enumerate(given_arguments) if s is NOTHING
    ] + [f"{name}={s!r}" for name, s in given_kwargs.items() if s is NOTHING]
    if empty:
        strats = "strategies" if len(empty) > 1 else "strategy"
        return invalid(
            f"Cannot generate examples from empty {strats}: " + ", ".join(empty),
            exc=Unsatisfiable,
        )


class ArtificialDataForExample(ConjectureData):
    """Dummy object that pretends to be a ConjectureData object for the purposes of
    drawing arguments for @example. Provides just enough of the ConjectureData API
    to allow the test to run. Does not support any sort of interactive drawing,
    but that's fine because you can't access that when all of your arguments are
    provided by @example.
    """

    def __init__(self, kwargs):
        self.__draws = 0
        self.__kwargs = kwargs
        super().__init__(max_length=0, prefix=b"", random=None)

    def draw_bits(self, n):
        raise NotImplementedError("Dummy object should never be asked for bits.")

    def draw(self, strategy):
        assert self.__draws == 0
        self.__draws += 1
        # The main strategy for given is always a tuples strategy that returns
        # first positional arguments then keyword arguments. When building this
        # object already converted all positional arguments to keyword arguments,
        # so this is the correct format to return.
        return (), self.__kwargs


def execute_explicit_examples(state, wrapped_test, arguments, kwargs):
    original_argspec = getfullargspec(state.test)

    for example in reversed(getattr(wrapped_test, "hypothesis_explicit_examples", ())):
        example_kwargs = dict(original_argspec.kwonlydefaults or {})
        if example.args:
            if len(example.args) > len(original_argspec.args):
                raise InvalidArgument(
                    "example has too many arguments for test. Expected at most "
                    f"{len(original_argspec.args)} but got {len(example.args)}"
                )
            example_kwargs.update(
                dict(zip(original_argspec.args[-len(example.args) :], example.args))
            )
        else:
            example_kwargs.update(example.kwargs)
        if Phase.explicit not in state.settings.phases:
            continue
        example_kwargs.update(kwargs)

        with local_settings(state.settings):
            fragments_reported = []
            try:
                with with_reporter(fragments_reported.append):
                    state.execute_once(
                        ArtificialDataForExample(example_kwargs),
                        is_final=True,
                        print_example=True,
                    )
            except UnsatisfiedAssumption:
                # Odd though it seems, we deliberately support explicit examples that
                # are then rejected by a call to `assume()`.  As well as iterative
                # development, this is rather useful to replay Hypothesis' part of
                # a saved failure when other arguments are supplied by e.g. pytest.
                # See https://github.com/HypothesisWorks/hypothesis/issues/2125
                pass
            except BaseException as err:
                # In order to support reporting of multiple failing examples, we yield
                # each of the (report text, error) pairs we find back to the top-level
                # runner.  This also ensures that user-facing stack traces have as few
                # frames of Hypothesis internals as possible.
                err = err.with_traceback(get_trimmed_traceback())

                # One user error - whether misunderstanding or typo - we've seen a few
                # times is to pass strategies to @example() where values are expected.
                # Checking is easy, and false-positives not much of a problem, so:
                if any(
                    isinstance(arg, SearchStrategy)
                    for arg in example.args + tuple(example.kwargs.values())
                ):
                    new = HypothesisWarning(
                        "The @example() decorator expects to be passed values, but "
                        "you passed strategies instead.  See https://hypothesis."
                        "readthedocs.io/en/latest/reproducing.html for details."
                    )
                    new.__cause__ = err
                    err = new

                yield (fragments_reported, err)
                if state.settings.report_multiple_bugs:
                    continue
                break
            finally:
                if fragments_reported:
                    assert fragments_reported[0].startswith("Falsifying example")
                    fragments_reported[0] = fragments_reported[0].replace(
                        "Falsifying example", "Falsifying explicit example", 1
                    )

            if fragments_reported:
                verbose_report(fragments_reported[0].replace("Falsifying", "Trying", 1))
                for f in fragments_reported[1:]:
                    verbose_report(f)


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
        global _hypothesis_global_random
        if _hypothesis_global_random is None:
            _hypothesis_global_random = Random()
        seed = _hypothesis_global_random.getrandbits(128)
        wrapped_test._hypothesis_internal_use_generated_seed = seed
        return Random(seed)


def process_arguments_to_given(wrapped_test, arguments, kwargs, given_kwargs, argspec):
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
            st.fixed_dictionaries(given_kwargs).map(lambda args: dict(args, **kwargs)),
        )
    )

    if selfy is not None:
        search_strategy = WithRunner(search_strategy, selfy)

    search_strategy.validate()

    return arguments, kwargs, test_runner, search_strategy


def skip_exceptions_to_reraise():
    """Return a tuple of exceptions meaning 'skip this test', to re-raise.

    This is intended to cover most common test runners; if you would
    like another to be added please open an issue or pull request adding
    it to this function and to tests/cover/test_lazy_import.py
    """
    # This is a set because nose may simply re-export unittest.SkipTest
    exceptions = set()
    # We use this sys.modules trick to avoid importing libraries -
    # you can't be an instance of a type from an unimported module!
    # This is fast enough that we don't need to cache the result,
    # and more importantly it avoids possible side-effects :-)
    if "unittest" in sys.modules:
        exceptions.add(sys.modules["unittest"].SkipTest)
    if "unittest2" in sys.modules:
        exceptions.add(sys.modules["unittest2"].SkipTest)
    if "nose" in sys.modules:
        exceptions.add(sys.modules["nose"].SkipTest)
    if "_pytest" in sys.modules:
        exceptions.add(sys.modules["_pytest"].outcomes.Skipped)
    return tuple(sorted(exceptions, key=str))


def failure_exceptions_to_catch():
    """Return a tuple of exceptions meaning 'this test has failed', to catch.

    This is intended to cover most common test runners; if you would
    like another to be added please open an issue or pull request.
    """
    # While SystemExit and GeneratorExit are instances of BaseException, we also
    # expect them to be deterministic - unlike KeyboardInterrupt - and so we treat
    # them as standard exceptions, check for flakiness, etc.
    # See https://github.com/HypothesisWorks/hypothesis/issues/2223 for details.
    exceptions = [Exception, SystemExit, GeneratorExit]
    if "_pytest" in sys.modules:
        exceptions.append(sys.modules["_pytest"].outcomes.Failed)
    return tuple(exceptions)


def new_given_argspec(original_argspec, given_kwargs):
    """Make an updated argspec for the wrapped test."""
    new_args = [a for a in original_argspec.args if a not in given_kwargs]
    new_kwonlyargs = [a for a in original_argspec.kwonlyargs if a not in given_kwargs]
    annots = {
        k: v
        for k, v in original_argspec.annotations.items()
        if k in new_args + new_kwonlyargs
    }
    annots["return"] = None
    return original_argspec._replace(
        args=new_args, kwonlyargs=new_kwonlyargs, annotations=annots
    )


class StateForActualGivenExecution:
    def __init__(
        self, test_runner, search_strategy, test, settings, random, wrapped_test
    ):
        self.test_runner = test_runner
        self.search_strategy = search_strategy
        self.settings = settings
        self.last_exception = None
        self.falsifying_examples = ()
        self.__was_flaky = False
        self.random = random
        self.__test_runtime = None

        self.is_find = getattr(wrapped_test, "_hypothesis_internal_is_find", False)
        self.wrapped_test = wrapped_test

        self.test = test

        self.print_given_args = getattr(
            wrapped_test, "_hypothesis_internal_print_given_args", True
        )

        self.files_to_propagate = set()
        self.failed_normally = False
        self.failed_due_to_deadline = False

        self.explain_traces = defaultdict(set)

    def execute_once(
        self, data, print_example=False, is_final=False, expected_failure=None
    ):
        """Run the test function once, using ``data`` as input.

        If the test raises an exception, it will propagate through to the
        caller of this method. Depending on its type, this could represent
        an ordinary test failure, or a fatal error, or a control exception.

        If this method returns normally, the test might have passed, or
        it might have placed ``data`` in an unsuccessful state and then
        swallowed the corresponding control exception.
        """

        data.is_find = self.is_find

        text_repr = None
        if self.settings.deadline is None:
            test = self.test
        else:

            @proxies(self.test)
            def test(*args, **kwargs):
                self.__test_runtime = None
                initial_draws = len(data.draw_times)
                start = time.perf_counter()
                result = self.test(*args, **kwargs)
                finish = time.perf_counter()
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
            # Set up dynamic context needed by a single test run.
            with local_settings(self.settings):
                with deterministic_PRNG():
                    with BuildContext(data, is_final=is_final):

                        # Generate all arguments to the test function.
                        args, kwargs = data.draw(self.search_strategy)
                        if expected_failure is not None:
                            nonlocal text_repr
                            text_repr = repr_call(test, args, kwargs)

                        if print_example or current_verbosity() >= Verbosity.verbose:
                            output = StringIO()

                            printer = RepresentationPrinter(output)
                            if print_example:
                                printer.text("Falsifying example:")
                            else:
                                printer.text("Trying example:")

                            if self.print_given_args:
                                printer.text(" ")
                                printer.text(test.__name__)
                                with printer.group(indent=4, open="(", close=""):
                                    printer.break_()
                                    for v in args:
                                        printer.pretty(v)
                                        # We add a comma unconditionally because
                                        # generated arguments will always be kwargs,
                                        # so there will always be more to come.
                                        printer.text(",")
                                        printer.breakable()

                                    for i, (k, v) in enumerate(kwargs.items()):
                                        printer.text(k)
                                        printer.text("=")
                                        printer.pretty(v)
                                        printer.text(",")
                                        if i + 1 < len(kwargs):
                                            printer.breakable()
                                printer.break_()
                                printer.text(")")
                            printer.flush()
                            report(output.getvalue())
                        return test(*args, **kwargs)

        # Run the test function once, via the executor hook.
        # In most cases this will delegate straight to `run(data)`.
        result = self.test_runner(data, run)

        # If a failure was expected, it should have been raised already, so
        # instead raise an appropriate diagnostic error.
        if expected_failure is not None:
            exception, traceback = expected_failure
            if (
                isinstance(exception, DeadlineExceeded)
                and self.__test_runtime is not None
            ):
                report(
                    "Unreliable test timings! On an initial run, this "
                    "test took %.2fms, which exceeded the deadline of "
                    "%.2fms, but on a subsequent run it took %.2f ms, "
                    "which did not. If you expect this sort of "
                    "variability in your test timings, consider turning "
                    "deadlines off for this test by setting deadline=None."
                    % (
                        exception.runtime.total_seconds() * 1000,
                        self.settings.deadline.total_seconds() * 1000,
                        self.__test_runtime.total_seconds() * 1000,
                    )
                )
            else:
                report("Failed to reproduce exception. Expected: \n" + traceback)
            self.__flaky(
                f"Hypothesis {text_repr} produces unreliable results: Falsified"
                " on the first call but did not on a subsequent one",
                cause=exception,
            )
        return result

    def _execute_once_for_engine(self, data):
        """Wrapper around ``execute_once`` that intercepts test failure
        exceptions and single-test control exceptions, and turns them into
        appropriate method calls to `data` instead.

        This allows the engine to assume that any exception other than
        ``StopTest`` must be a fatal error, and should stop the entire engine.
        """
        try:
            trace = frozenset()
            if (
                self.failed_normally
                and not self.failed_due_to_deadline
                and Phase.shrink in self.settings.phases
                and Phase.explain in self.settings.phases
                and sys.gettrace() is None
                and not PYPY
            ):  # pragma: no cover
                # This is in fact covered by our *non-coverage* tests, but due to the
                # settrace() contention *not* by our coverage tests.  Ah well.
                tracer = Tracer()
                try:
                    sys.settrace(tracer.trace)
                    result = self.execute_once(data)
                    if data.status == Status.VALID:
                        self.explain_traces[None].add(frozenset(tracer.branches))
                finally:
                    sys.settrace(None)
                    trace = frozenset(tracer.branches)
            else:
                result = self.execute_once(data)
            if result is not None:
                fail_health_check(
                    self.settings,
                    "Tests run under @given should return None, but "
                    f"{self.test.__name__} returned {result!r} instead.",
                    HealthCheck.return_value,
                )
        except UnsatisfiedAssumption:
            # An "assume" check failed, so instead we inform the engine that
            # this test run was invalid.
            data.mark_invalid()
        except StopTest:
            # The engine knows how to handle this control exception, so it's
            # OK to re-raise it.
            raise
        except (
            HypothesisDeprecationWarning,
            FailedHealthCheck,
        ) + skip_exceptions_to_reraise():
            # These are fatal errors or control exceptions that should stop the
            # engine, so we re-raise them.
            raise
        except failure_exceptions_to_catch() as e:
            # If the error was raised by Hypothesis-internal code, re-raise it
            # as a fatal error instead of treating it as a test failure.
            escalate_hypothesis_internal_error()

            if data.frozen:
                # This can happen if an error occurred in a finally
                # block somewhere, suppressing our original StopTest.
                # We raise a new one here to resume normal operation.
                raise StopTest(data.testcounter) from e
            else:
                # The test failed by raising an exception, so we inform the
                # engine that this test run was interesting. This is the normal
                # path for test runs that fail.

                tb = get_trimmed_traceback()
                info = data.extra_information
                info.__expected_traceback = format_exception(e, tb)
                info.__expected_exception = e
                verbose_report(info.__expected_traceback)

                self.failed_normally = True

                interesting_origin = get_interesting_origin(e)
                if trace:  # pragma: no cover
                    # Trace collection is explicitly disabled under coverage.
                    self.explain_traces[interesting_origin].add(trace)
                if interesting_origin[0] == DeadlineExceeded:
                    self.failed_due_to_deadline = True
                    self.explain_traces.clear()
                data.mark_interesting(interesting_origin)

    def run_engine(self):
        """Run the test function many times, on database input and generated
        input, using the Conjecture engine.
        """
        # Tell pytest to omit the body of this function from tracebacks
        __tracebackhide__ = True
        try:
            database_key = self.wrapped_test._hypothesis_internal_database_key
        except AttributeError:
            if global_force_seed is None:
                database_key = function_digest(self.test)
            else:
                database_key = None

        runner = ConjectureRunner(
            self._execute_once_for_engine,
            settings=self.settings,
            random=self.random,
            database_key=database_key,
        )
        # Use the Conjecture engine to run the test function many times
        # on different inputs.
        runner.run()
        note_statistics(runner.statistics)

        if runner.call_count == 0:
            return
        if runner.interesting_examples:
            self.falsifying_examples = sorted(
                runner.interesting_examples.values(),
                key=lambda d: sort_key(d.buffer),
                reverse=True,
            )
        else:
            if runner.valid_examples == 0:
                rep = get_pretty_function_description(self.test)
                raise Unsatisfiable(f"Unable to satisfy assumptions of {rep}")

        if not self.falsifying_examples:
            return
        elif not self.settings.report_multiple_bugs:
            # Pretend that we only found one failure, by discarding the others.
            del self.falsifying_examples[:-1]

        # The engine found one or more failures, so we need to reproduce and
        # report them.

        flaky = 0

        if runner.best_observed_targets:
            for line in describe_targets(runner.best_observed_targets):
                report(line)
            report("")

        explanations = explanatory_lines(self.explain_traces, self.settings)
        for falsifying_example in self.falsifying_examples:
            info = falsifying_example.extra_information

            ran_example = ConjectureData.for_buffer(falsifying_example.buffer)
            self.__was_flaky = False
            assert info.__expected_exception is not None
            try:
                self.execute_once(
                    ran_example,
                    print_example=not self.is_find,
                    is_final=True,
                    expected_failure=(
                        info.__expected_exception,
                        info.__expected_traceback,
                    ),
                )
            except (UnsatisfiedAssumption, StopTest) as e:
                report(format_exception(e, e.__traceback__))
                self.__flaky(
                    "Unreliable assumption: An example which satisfied "
                    "assumptions on the first run now fails it.",
                    cause=e,
                )
            except BaseException as e:
                # If we have anything for explain-mode, this is the time to report.
                for line in explanations[falsifying_example.interesting_origin]:
                    report(line)

                if len(self.falsifying_examples) <= 1:
                    # There is only one failure, so we can report it by raising
                    # it directly.
                    raise

                # We are reporting multiple failures, so we need to manually
                # print each exception's stack trace and information.
                tb = get_trimmed_traceback()
                report(format_exception(e, tb))

            finally:
                # Whether or not replay actually raised the exception again, we want
                # to print the reproduce_failure decorator for the failing example.
                if self.settings.print_blob:
                    report(
                        "\nYou can reproduce this example by temporarily adding "
                        "@reproduce_failure(%r, %r) as a decorator on your test case"
                        % (__version__, encode_failure(falsifying_example.buffer))
                    )
                # Mostly useful for ``find`` and ensuring that objects that
                # hold on to a reference to ``data`` know that it's now been
                # finished and they can't draw more data from it.
                ran_example.freeze()

            if self.__was_flaky:
                flaky += 1

        # If we only have one example then we should have raised an error or
        # flaky prior to this point.
        assert len(self.falsifying_examples) > 1

        if flaky > 0:
            raise Flaky(
                f"Hypothesis found {len(self.falsifying_examples)} distinct failures, "
                f"but {flaky} of them exhibited some sort of flaky behaviour."
            )
        else:
            raise MultipleFailures(
                f"Hypothesis found {len(self.falsifying_examples)} distinct failures."
            )

    def __flaky(self, message, *, cause):
        if len(self.falsifying_examples) <= 1:
            raise Flaky(message) from cause
        else:
            self.__was_flaky = True
            report("Flaky example! " + message)


@contextlib.contextmanager
def fake_subTest(self, msg=None, **__):
    """Monkeypatch for `unittest.TestCase.subTest` during `@given`.

    If we don't patch this out, each failing example is reported as a
    separate failing test by the unittest test runner, which is
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
class HypothesisHandle:
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
    _get_fuzz_target = attr.ib()
    _given_kwargs = attr.ib()

    @property
    def fuzz_one_input(
        self,
    ) -> Callable[[Union[bytes, bytearray, memoryview, BinaryIO]], Optional[bytes]]:
        """Run the test as a fuzz target, driven with the `buffer` of bytes.

        Returns None if buffer invalid for the strategy, canonical pruned
        bytes if the buffer was valid, and leaves raised exceptions alone.
        """
        # Note: most users, if they care about fuzzer performance, will access the
        # property and assign it to a local variable to move the attribute lookup
        # outside their fuzzing loop / before the fork point.  We cache it anyway,
        # so that naive or unusual use-cases get the best possible performance too.
        try:
            return self.__cached_target  # type: ignore
        except AttributeError:
            self.__cached_target = self._get_fuzz_target()
            return self.__cached_target


@overload
def given(
    *_given_arguments: Union[SearchStrategy[Any], InferType],
) -> Callable[
    [Callable[..., Union[None, Coroutine[Any, Any, None]]]], Callable[..., None]
]:  # pragma: no cover
    ...


@overload
def given(
    **_given_kwargs: Union[SearchStrategy[Any], InferType],
) -> Callable[
    [Callable[..., Union[None, Coroutine[Any, Any, None]]]], Callable[..., None]
]:  # pragma: no cover
    ...


def given(
    *_given_arguments: Union[SearchStrategy[Any], InferType],
    **_given_kwargs: Union[SearchStrategy[Any], InferType],
) -> Callable[
    [Callable[..., Union[None, Coroutine[Any, Any, None]]]], Callable[..., None]
]:
    """A decorator for turning a test function that accepts arguments into a
    randomized test.

    This is the main entry point to Hypothesis.
    """

    def run_test_as_given(test):
        if inspect.isclass(test):
            # Provide a meaningful error to users, instead of exceptions from
            # internals that assume we're dealing with a function.
            raise InvalidArgument("@given cannot be applied to a class.")
        given_arguments = tuple(_given_arguments)
        given_kwargs = dict(_given_kwargs)

        original_argspec = getfullargspec(test)

        if given_arguments == (Ellipsis,) and not given_kwargs:
            # user indicated that they want to infer all arguments
            given_kwargs.update(
                (name, Ellipsis)
                for name in chain(original_argspec.args, original_argspec.kwonlyargs)
            )
            given_arguments = ()

        check_invalid = is_invalid_test(
            test, original_argspec, given_arguments, given_kwargs
        )

        # If the argument check found problems, return a dummy test function
        # that will raise an error if it is actually called.
        if check_invalid is not None:
            return check_invalid

        # Because the argument check succeeded, we can convert @given's
        # positional arguments into keyword arguments for simplicity.
        if given_arguments:
            assert not given_kwargs
            nargs = len(given_arguments)
            given_kwargs.update(zip(original_argspec.args[-nargs:], given_arguments))
        # These have been converted, so delete them to prevent accidental use.
        del given_arguments

        argspec = new_given_argspec(original_argspec, given_kwargs)

        # Use type information to convert "infer" arguments into appropriate strategies.
        if infer in given_kwargs.values():
            hints = get_type_hints(test)
        for name in [name for name, value in given_kwargs.items() if value is infer]:
            if name not in hints:
                # As usual, we want to emit this error when the test is executed,
                # not when it's decorated.

                @impersonate(test)
                @define_function_signature(test.__name__, test.__doc__, argspec)
                def wrapped_test(*arguments, **kwargs):
                    __tracebackhide__ = True
                    raise InvalidArgument(
                        f"passed {name}=... for {test.__name__}, but {name} has "
                        "no type annotation"
                    )

                return wrapped_test

            given_kwargs[name] = st.from_type(hints[name])

        @impersonate(test)
        @define_function_signature(test.__name__, test.__doc__, argspec)
        def wrapped_test(*arguments, **kwargs):
            # Tell pytest to omit the body of this function from tracebacks
            __tracebackhide__ = True

            test = wrapped_test.hypothesis.inner_test

            if getattr(test, "is_hypothesis_test", False):
                raise InvalidArgument(
                    f"You have applied @given to the test {test.__name__} more than "
                    "once, which wraps the test several times and is extremely slow. "
                    "A similar effect can be gained by combining the arguments "
                    "of the two calls to given. For example, instead of "
                    "@given(booleans()) @given(integers()), you could write "
                    "@given(booleans(), integers())"
                )

            settings = wrapped_test._hypothesis_internal_use_settings

            random = get_random_for_wrapped_test(test, wrapped_test)

            processed_args = process_arguments_to_given(
                wrapped_test, arguments, kwargs, given_kwargs, argspec
            )
            arguments, kwargs, test_runner, search_strategy = processed_args

            if (
                inspect.iscoroutinefunction(test)
                and test_runner is default_new_style_executor
            ):
                # See https://github.com/HypothesisWorks/hypothesis/issues/3054
                # If our custom executor doesn't handle coroutines, or we return an
                # awaitable from a non-async-def function, we just rely on the
                # return_value health check.  This catches most user errors though.
                raise InvalidArgument(
                    "Hypothesis doesn't know how to run async test functions like "
                    f"{test.__name__}.  You'll need to write a custom executor, "
                    "or use a library like pytest-asyncio or pytest-trio which can "
                    "handle the translation for you.\n    See https://hypothesis."
                    "readthedocs.io/en/latest/details.html#custom-function-execution"
                )

            runner = getattr(search_strategy, "runner", None)
            if isinstance(runner, TestCase) and test.__name__ in dir(TestCase):
                msg = (
                    f"You have applied @given to the method {test.__name__}, which is "
                    "used by the unittest runner but is not itself a test."
                    "  This is not useful in any way."
                )
                fail_health_check(settings, msg, HealthCheck.not_a_test_method)
            if bad_django_TestCase(runner):  # pragma: no cover
                # Covered by the Django tests, but not the pytest coverage task
                raise InvalidArgument(
                    "You have applied @given to a method on "
                    f"{type(runner).__qualname__}, but this "
                    "class does not inherit from the supported versions in "
                    "`hypothesis.extra.django`.  Use the Hypothesis variants "
                    "to ensure that each example is run in a separate "
                    "database transaction."
                )

            state = StateForActualGivenExecution(
                test_runner, search_strategy, test, settings, random, wrapped_test
            )

            reproduce_failure = wrapped_test._hypothesis_internal_use_reproduce_failure

            # If there was a @reproduce_failure decorator, use it to reproduce
            # the error (or complain that we couldn't). Either way, this will
            # always raise some kind of error.
            if reproduce_failure is not None:
                expected_version, failure = reproduce_failure
                if expected_version != __version__:
                    raise InvalidArgument(
                        "Attempting to reproduce a failure from a different "
                        "version of Hypothesis. This failure is from %s, but "
                        "you are currently running %r. Please change your "
                        "Hypothesis version to a matching one."
                        % (expected_version, __version__)
                    )
                try:
                    state.execute_once(
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
                    ) from None
                except UnsatisfiedAssumption:
                    raise DidNotReproduce(
                        "The test data failed to satisfy an assumption in the "
                        "test. Have you added it since this blob was "
                        "generated?"
                    ) from None

            # There was no @reproduce_failure, so start by running any explicit
            # examples from @example decorators.
            errors = list(
                execute_explicit_examples(state, wrapped_test, arguments, kwargs)
            )
            with local_settings(state.settings):
                if len(errors) > 1:
                    # If we're not going to report multiple bugs, we would have
                    # stopped running explicit examples at the first failure.
                    assert state.settings.report_multiple_bugs
                    for fragments, err in errors:
                        for f in fragments:
                            report(f)
                        report(format_exception(err, err.__traceback__))
                    raise MultipleFailures(
                        f"Hypothesis found {len(errors)} failures in explicit examples."
                    )
                elif errors:
                    fragments, the_error_hypothesis_found = errors[0]
                    for f in fragments:
                        report(f)
                    raise the_error_hypothesis_found

            # If there were any explicit examples, they all ran successfully.
            # The next step is to use the Conjecture engine to run the test on
            # many different inputs.

            if not (
                Phase.reuse in settings.phases or Phase.generate in settings.phases
            ):
                return

            try:
                if isinstance(runner, TestCase) and hasattr(runner, "subTest"):
                    subTest = runner.subTest
                    try:
                        runner.subTest = types.MethodType(fake_subTest, runner)
                        state.run_engine()
                    finally:
                        runner.subTest = subTest
                else:
                    state.run_engine()
            except BaseException as e:
                # The exception caught here should either be an actual test
                # failure (or MultipleFailures), or some kind of fatal error
                # that caused the engine to stop.

                generated_seed = wrapped_test._hypothesis_internal_use_generated_seed
                with local_settings(settings):
                    if not (state.failed_normally or generated_seed is None):
                        if running_under_pytest:
                            report(
                                f"You can add @seed({generated_seed}) to this test or "
                                f"run pytest with --hypothesis-seed={generated_seed} "
                                "to reproduce this failure."
                            )
                        else:
                            report(
                                f"You can add @seed({generated_seed}) to this test to "
                                "reproduce this failure."
                            )
                    # The dance here is to avoid showing users long tracebacks
                    # full of Hypothesis internals they don't care about.
                    # We have to do this inline, to avoid adding another
                    # internal stack frame just when we've removed the rest.
                    #
                    # Using a variable for our trimmed error ensures that the line
                    # which will actually appear in tracebacks is as clear as
                    # possible - "raise the_error_hypothesis_found".
                    the_error_hypothesis_found = e.with_traceback(
                        get_trimmed_traceback()
                    )
                    raise the_error_hypothesis_found

        def _get_fuzz_target() -> Callable[
            [Union[bytes, bytearray, memoryview, BinaryIO]], Optional[bytes]
        ]:
            # Because fuzzing interfaces are very performance-sensitive, we use a
            # somewhat more complicated structure here.  `_get_fuzz_target()` is
            # called by the `HypothesisHandle.fuzz_one_input` property, allowing
            # us to defer our collection of the settings, random instance, and
            # reassignable `inner_test` (etc) until `fuzz_one_input` is accessed.
            #
            # We then share the performance cost of setting up `state` between
            # many invocations of the target.  We explicitly force `deadline=None`
            # for performance reasons, saving ~40% the runtime of an empty test.
            test = wrapped_test.hypothesis.inner_test
            settings = Settings(
                parent=wrapped_test._hypothesis_internal_use_settings, deadline=None
            )
            random = get_random_for_wrapped_test(test, wrapped_test)
            _args, _kwargs, test_runner, search_strategy = process_arguments_to_given(
                wrapped_test, (), {}, given_kwargs, argspec
            )
            assert not _args
            assert not _kwargs
            state = StateForActualGivenExecution(
                test_runner, search_strategy, test, settings, random, wrapped_test
            )
            digest = function_digest(test)
            # We track the minimal-so-far example for each distinct origin, so
            # that we track log-n instead of n examples for long runs.  In particular
            # it means that we saturate for common errors in long runs instead of
            # storing huge volumes of low-value data.
            minimal_failures: dict = {}

            def fuzz_one_input(
                buffer: Union[bytes, bytearray, memoryview, BinaryIO]
            ) -> Optional[bytes]:
                # This inner part is all that the fuzzer will actually run,
                # so we keep it as small and as fast as possible.
                if isinstance(buffer, io.IOBase):
                    buffer = buffer.read()
                assert isinstance(buffer, (bytes, bytearray, memoryview))
                data = ConjectureData.for_buffer(buffer)
                try:
                    state.execute_once(data)
                except (StopTest, UnsatisfiedAssumption):
                    return None
                except BaseException:
                    buffer = bytes(data.buffer)
                    known = minimal_failures.get(data.interesting_origin)
                    if settings.database is not None and (
                        known is None or sort_key(buffer) <= sort_key(known)
                    ):
                        settings.database.save(digest, buffer)
                        minimal_failures[data.interesting_origin] = buffer
                    raise
                return bytes(data.buffer)

            fuzz_one_input.__doc__ = HypothesisHandle.fuzz_one_input.__doc__
            return fuzz_one_input

        # After having created the decorated test function, we need to copy
        # over some attributes to make the switch as seamless as possible.

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
        wrapped_test.hypothesis = HypothesisHandle(test, _get_fuzz_target, given_kwargs)
        return wrapped_test

    return run_test_as_given


def find(
    specifier: SearchStrategy[Ex],
    condition: Callable[[Any], bool],
    *,
    settings: Optional[Settings] = None,
    random: Optional[Random] = None,
    database_key: Optional[bytes] = None,
) -> Ex:
    """Returns the minimal example from the given strategy ``specifier`` that
    matches the predicate function ``condition``."""
    if settings is None:
        settings = Settings(max_examples=2000)
    settings = Settings(
        settings, suppress_health_check=HealthCheck.all(), report_multiple_bugs=False
    )

    if database_key is None and settings.database is not None:
        database_key = function_digest(condition)

    if not isinstance(specifier, SearchStrategy):
        raise InvalidArgument(
            f"Expected SearchStrategy but got {specifier!r} of "
            f"type {type(specifier).__name__}"
        )
    specifier.validate()

    last: List[Ex] = []

    @settings
    @given(specifier)
    def test(v):
        if condition(v):
            last[:] = [v]
            raise Found()

    if random is not None:
        test = seed(random.getrandbits(64))(test)

    # Aliasing as Any avoids mypy errors (attr-defined) when accessing and
    # setting custom attributes on the decorated function or class.
    _test: Any = test
    _test._hypothesis_internal_is_find = True
    _test._hypothesis_internal_database_key = database_key

    try:
        test()
    except Found:
        return last[0]

    raise NoSuchExample(get_pretty_function_description(condition))
